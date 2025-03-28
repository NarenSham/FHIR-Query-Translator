import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Dict, Any, Optional
import re

class QueryTranslator:
    def __init__(self, db_config: Dict[str, str], api_key: str):
        # Add debug logging for connection
        print("Attempting to connect with config:", {
            k: v for k, v in db_config.items() if k != 'password'
        })
        self.db_config = db_config
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-1.5-flash-8b-exp-0924')  # Using full model name with prefix
        
        # Updated schema information to include all tables
        self.schema_context = """
        Available tables and their structures:
        
        patients:
        - id (uuid): unique identifier
        - resource_id (text): external identifier
        - gender (text): patient's gender
        - birth_date (date): date of birth
        - deceased_date (timestamp): date of death if applicable
        - marital_status (jsonb): marital status information
        - data (jsonb): full FHIR resource data
        
        encounters:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - status (text): encounter status
        - class (jsonb): encounter class
        - type (jsonb): encounter type
        - period_start (timestamp): when encounter started
        - period_end (timestamp): when encounter ended
        - data (jsonb): full FHIR resource data
        
        conditions:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - encounter_id (uuid): reference to encounters table
        - code (jsonb): condition code
        - clinical_status (jsonb): status of the condition
        - verification_status (jsonb): verification status
        - onset_date (timestamp): when condition started
        - abatement_date (timestamp): when condition ended/resolved
        - data (jsonb): full FHIR resource data
        
        diagnostic_reports:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - encounter_id (uuid): reference to encounters table
        - status (text): report status
        - effective_date (timestamp): when test was performed
        - issued (timestamp): when report was issued
        - data (jsonb): full FHIR resource data
        
        document_references:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - encounter_id (uuid): reference to encounters table
        - status (text): document status
        - type (jsonb): document type
        - date (timestamp): document date
        - data (jsonb): full FHIR resource data
        
        claims:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - status (text): claim status
        - type (jsonb): claim type
        - use (text): claim use
        - billable_period_start (timestamp): start of billable period
        - billable_period_end (timestamp): end of billable period
        - data (jsonb): full FHIR resource data
        
        explanations_of_benefit:
        - id (uuid): unique identifier
        - patient_id (uuid): reference to patients table
        - claim_id (uuid): reference to claims table
        - status (text): EOB status
        - type (jsonb): EOB type
        - use (text): EOB use
        - data (jsonb): full FHIR resource data
        
        Common relationships:
        - All tables link to patients through patient_id
        - encounters, conditions, diagnostic_reports, and document_references are linked through encounter_id
        - explanations_of_benefit links to claims through claim_id
        
        Notes:
        - All tables include a data column containing the full FHIR resource as JSONB
        - JSONB fields can be queried using -> or ->> operators
        - Timestamps should be handled using PostgreSQL timestamp functions
        """
        
        # Add visualization type decision rules
        self.visualization_rules = {
            "comparison": {
                "among_items": {
                    "one_variable": ["bar_chart_vertical", "bar_chart_horizontal"],
                    "two_variables": ["variable_width_column_chart", "table_with_charts"],
                    "many_categories": ["table_with_charts"]
                },
                "over_time": {
                    "few_categories": ["line_chart", "bar_chart_vertical"],
                    "cyclical": ["circular_area_chart"],
                    "non_cyclical": ["line_chart"]
                }
            },
            "relationship": {
                "two_variables": ["scatter_plot"],
                "three_or_more": ["bubble_chart"]
            },
            "distribution": {
                "few_points": ["bar_histogram"],
                "many_points": ["line_histogram", "scatter_plot"]
            },
            "composition": {
                "static": ["pie_chart"],
                "changing_over_time": {
                    "few_periods": {
                        "relative_only": ["stacked_100_bar_chart"],
                        "absolute_and_relative": ["stacked_bar_chart"]
                    },
                    "many_periods": {
                        "relative_only": ["stacked_area_100_chart"],
                        "absolute_and_relative": ["stacked_area_chart"]
                    }
                },
                "accumulation": {
                    "to_total": ["waterfall_chart"],
                    "components": ["stacked_100_bar_subcomponents"],
                    "difference_matters": ["tree_map"]
                }
            }
        }
        
    def generate_sql_query(self, user_question: str) -> str:
        """Convert natural language question to SQL query using Gemini"""
        
        # Add these JSONB extraction patterns to the prompt
        jsonb_extraction_examples = """
        Instead of selecting JSONB columns directly, extract specific fields:
        
        -- For patient names (FHIR format):
        p.data->'name'->0->'given'->0->>'value' as given_name,
        p.data->'name'->0->>'family' as family_name,
        
        -- For addresses (FHIR format):
        p.data->'address'->0->>'city' as city,
        p.data->'address'->0->>'state' as state,
        p.data->'address'->0->>'postalCode' as postal_code,
        p.data->'address'->0->>'line' as street_address,
        
        -- For condition codes:
        c.code->>'code' as condition_code_value,
        
        -- For clinical status:
        c.clinical_status->>'coding' as clinical_status_value,
        
        -- For encounter class:
        e.class->>'code' as encounter_class_code,
        e.class->>'display' as encounter_class_display,
        
        -- For encounter type:
        e.type->0->>'coding' as encounter_type_code,
        
        -- For document type:
        doc.type->'coding'->0->>'code' as document_type_code,
        doc.type->'coding'->0->>'display' as document_type_display,
        
        -- For marital status:
        p.marital_status->'coding'->0->>'code' as marital_status_code,
        p.marital_status->'coding'->0->>'display' as marital_status_display
        """

        prompt = f"""
        Given the following database schema:
        {self.schema_context}
        
        Important FHIR data structure rules:
        1. NEVER return raw JSONB columns directly - always extract specific fields
        2. Use -> for navigating through JSON objects and arrays
        3. Use ->> only for final text extraction
        4. For JSONB fields, extract meaningful values using proper JSON paths
        5. For addresses, use p.data->'address'->0->>'city' to get city
        6. For patient counts by location, group by the extracted city field
        
        {jsonb_extraction_examples}
        
        Example correct queries:
        
        -- Query for patient count by city:
        SELECT 
            p.data->'address'->0->>'city' as city,
            COUNT(*) as patient_count
        FROM patients p
        WHERE p.data->'address'->0->>'city' IS NOT NULL
        GROUP BY p.data->'address'->0->>'city'
        ORDER BY patient_count DESC;
        
        -- Query for patients in a specific city:
        SELECT 
            p.id,
            p.data->'name'->0->'given'->0->>'value' as given_name,
            p.data->'name'->0->>'family' as family_name,
            p.data->'address'->0->>'city' as city
        FROM patients p
        WHERE p.data->'address'->0->>'city' = 'Boston';
        
        Convert this question into a SQL query:
        "{user_question}"
        
        Rules:
        - Return ONLY the raw SQL query
        - Always extract specific fields from JSONB columns using proper JSON paths
        - Never return raw JSONB columns without extraction
        - Use appropriate column aliases for all extracted fields
        """
        
        response = self.model.generate_content(prompt)
        sql_query = response.text.strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        return sql_query
    
    def execute_query(self, sql_query: str, params: tuple = ()) -> list:
        """Execute the generated SQL query and return results"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql_query, params)  # Use parameterized query
            results = cur.fetchall()
            cur.close()
            conn.close()
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    def determine_visualization(self, results: list, sql_query: str) -> Dict[str, Any]:
        """Determine the appropriate D3 visualization based on query results and SQL query"""
        if not results or not isinstance(results, list):
            return {"type": None, "reason": "No results to visualize"}

        # Analyze the structure of the results
        sample = results[0]
        num_columns = len(sample.keys())
        num_rows = len(results)
        
        # Identify column types
        numeric_columns = []
        temporal_columns = []
        categorical_columns = []
        
        for key in sample.keys():
            value = sample[key]
            if isinstance(value, (int, float)):
                numeric_columns.append(key)
            elif isinstance(value, str):
                # Check if it's a date string
                if any(date_word in key.lower() for date_word in ['date', 'time', 'period']):
                    temporal_columns.append(key)
                else:
                    categorical_columns.append(key)

        # Analyze SQL query for hints
        sql_lower = sql_query.lower()
        is_count_query = 'count(' in sql_lower
        is_group_by = 'group by' in sql_lower
        is_time_series = any(term in sql_lower for term in ['date', 'timestamp', 'interval'])
        
        visualization_info = {
            "type": None,
            "config": {
                "data": results,
                "mapping": {}
            }
        }

        # Count by category visualization (e.g., patients by city)
        if is_count_query and is_group_by and len(categorical_columns) == 1 and len(numeric_columns) == 1:
            if num_rows <= 10:
                visualization_info["type"] = "bar_chart_vertical"
                visualization_info["config"]["mapping"] = {
                    "x": categorical_columns[0],
                    "y": numeric_columns[0]
                }
            else:
                visualization_info["type"] = "bar_chart_horizontal"
                visualization_info["config"]["mapping"] = {
                    "y": categorical_columns[0],
                    "x": numeric_columns[0]
                }
            return visualization_info

        # Time series data
        if temporal_columns and numeric_columns and is_time_series:
            visualization_info["type"] = "line_chart"
            visualization_info["config"]["mapping"] = {
                "x": temporal_columns[0],
                "y": numeric_columns[0]
            }
            return visualization_info

        # Distribution analysis
        if len(numeric_columns) == 1 and num_rows > 10:
            visualization_info["type"] = "bar_histogram"
            visualization_info["config"]["mapping"] = {
                "value": numeric_columns[0]
            }
            return visualization_info

        # Categorical composition (pie chart for small number of categories)
        if len(categorical_columns) == 1 and len(numeric_columns) == 1 and num_rows <= 8:
            visualization_info["type"] = "pie_chart"
            visualization_info["config"]["mapping"] = {
                "category": categorical_columns[0],
                "value": numeric_columns[0]
            }
            return visualization_info

        # Relationship between two numeric variables
        if len(numeric_columns) == 2:
            visualization_info["type"] = "scatter_plot"
            visualization_info["config"]["mapping"] = {
                "x": numeric_columns[0],
                "y": numeric_columns[1]
            }
            return visualization_info

        # Default to vertical bar chart for simple categorical comparisons
        if categorical_columns and numeric_columns:
            visualization_info["type"] = "bar_chart_vertical"
            visualization_info["config"]["mapping"] = {
                "x": categorical_columns[0],
                "y": numeric_columns[0]
            }
            return visualization_info

        return visualization_info

    def process_question(self, user_question: str) -> Dict[str, Any]:
        """Process user question and return results with metadata and visualization"""
        try:
            sql_query = self.generate_sql_query(user_question)
            results = self.execute_query(sql_query)
            
            # Generate visualization configuration
            visualization = self.determine_visualization(results, sql_query)
            
            return {
                "question": user_question,
                "sql_query": sql_query,
                "results": results,
                "visualization": visualization,
                "success": True
            }
        except Exception as e:
            return {
                "question": user_question,
                "error": str(e),
                "success": False
            }
