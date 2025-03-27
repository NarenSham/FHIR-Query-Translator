import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Dict, Any, Optional
import re

class QueryTranslator:
    def __init__(self, db_config: Dict[str, str], api_key: str):
        self.db_config = db_config
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-1.5-pro')  # Updated to use 1.5 version
        
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
        
    def generate_sql_query(self, user_question: str) -> str:
        """Convert natural language question to SQL query using Gemini"""
        
        # Add these JSONB extraction patterns to the prompt
        jsonb_extraction_examples = """
        Instead of selecting JSONB columns directly, extract specific fields:
        
        -- For condition codes:
        c.code->>'code' as condition_code_value,
        c.code->'coding'->0->>'display' as condition_display,
        
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
        
        -- For patient names:
        p.data->'name'->0->'given'->0->>'value' as given_name,
        p.data->'name'->0->>'family' as family_name,
        
        -- For addresses:
        p.data->'address'->0->>'line' as address_line,
        p.data->'address'->0->>'city' as city,
        p.data->'address'->0->>'state' as state,
        p.data->'address'->0->>'postalCode' as postal_code
        """

        prompt = f"""
        Given the following database schema:
        {self.schema_context}
        
        Important FHIR data structure rules:
        1. NEVER return raw JSONB columns directly - always extract specific fields
        2. Use -> for navigating through JSON objects and arrays
        3. Use ->> only for final text extraction
        4. For JSONB fields, extract meaningful values using proper JSON paths
        
        {jsonb_extraction_examples}
        
        Example correct query:
        SELECT 
            p.id as patient_id,
            p.gender,
            p.birth_date,
            p.marital_status->'coding'->0->>'display' as marital_status,
            c.code->'coding'->0->>'display' as condition_name,
            c.clinical_status->>'code' as clinical_status,
            e.class->>'code' as encounter_class
        FROM patients p
        LEFT JOIN encounters e ON p.id = e.patient_id
        LEFT JOIN conditions c ON p.id = c.patient_id;
        
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
        
        # Enhanced validation and correction of JSON paths
        def fix_json_path(query):
            # Common incorrect patterns and their corrections
            replacements = [
                # Fix incorrect name access patterns
                (r"data->>'name'->", r"data->'name'->"),
                (r"data->>'name'\s*->", r"data->'name'->"),
                (r"->>'given'->", r"->'given'->"),
                (r"->>'given'\s*->", r"->'given'->"),
                # Fix incorrect array access
                (r"'name'->>\d+", r"'name'->\0"),
                (r"'given'->>\d+", r"'given'->\0"),
                # Fix incorrect address access
                (r"data->>'address'->", r"data->'address'->"),
                (r"data->>'address'\s*->", r"data->'address'->"),
                # Fix incorrect array indexing
                (r"->>\d+->", r"->\0->"),
                (r"->>\d+\s*->", r"->\0->"),
            ]
            
            # Apply all replacements
            fixed_query = query
            for pattern, replacement in replacements:
                fixed_query = re.sub(pattern, replacement, fixed_query)
            
            # Ensure proper FHIR name search pattern
            if "WHERE" in fixed_query and "name" in fixed_query and "LIKE" in fixed_query:
                # Check if we need to convert to EXISTS clause
                if not "EXISTS" in fixed_query and ("data->'name'" in fixed_query or "data->>'name'" in fixed_query):
                    # Extract the name search condition
                    match = re.search(r"WHERE.*?(data.*?LIKE\s*'[^']*')", fixed_query, re.IGNORECASE)
                    if match:
                        old_condition = match.group(1)
                        new_condition = f"""
                        EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements(data->'name') n,
                                 jsonb_array_elements(n->'given') g
                            WHERE g->>'value' LIKE {old_condition.split("LIKE")[1].strip()}
                        )"""
                        fixed_query = fixed_query.replace(old_condition, new_condition)
            
            return fixed_query
        
        # Apply the fixes
        sql_query = fix_json_path(sql_query)
        
        # Validate the query still has essential components
        if not all(keyword in sql_query.upper() for keyword in ['SELECT', 'FROM']):
            raise ValueError("Generated SQL query is missing essential components")
        
        return sql_query
    
    def execute_query(self, sql_query: str) -> list:
        """Execute the generated SQL query and return results"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql_query)
            results = cur.fetchall()
            cur.close()
            conn.close()
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    def process_question(self, user_question: str) -> Dict[str, Any]:
        """Process user question and return results with metadata"""
        try:
            sql_query = self.generate_sql_query(user_question)
            results = self.execute_query(sql_query)
            
            return {
                "question": user_question,
                "sql_query": sql_query,
                "results": results,
                "success": True
            }
        except Exception as e:
            return {
                "question": user_question,
                "error": str(e),
                "success": False
            }
