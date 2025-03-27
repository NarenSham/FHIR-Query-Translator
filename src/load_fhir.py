import json
import glob
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
import uuid

def parse_fhir_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        return None

def validate_data_load(cur):
    # Get counts for each table
    tables = ['patients', 'encounters', 'conditions', 'diagnostic_reports', 
              'document_references', 'claims', 'explanations_of_benefit']
    counts = {}
    
    print("\nValidating data load:")
    print("-" * 50)
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        counts[table] = count
        print(f"{table}: {count:,} records")

    # Validate referential integrity
    print("\nValidating referential integrity:")
    print("-" * 50)
    
    # Check encounters -> patients
    cur.execute("""
        SELECT COUNT(*) FROM encounters e 
        LEFT JOIN patients p ON e.patient_id = p.id 
        WHERE p.id IS NULL
    """)
    orphaned = cur.fetchone()[0]
    print(f"Orphaned encounters (no patient): {orphaned}")

    # Check conditions -> patients/encounters
    cur.execute("""
        SELECT COUNT(*) FROM conditions c 
        LEFT JOIN patients p ON c.patient_id = p.id 
        WHERE p.id IS NULL
    """)
    orphaned = cur.fetchone()[0]
    print(f"Orphaned conditions (no patient): {orphaned}")

    # Check diagnostic reports -> patients/encounters
    cur.execute("""
        SELECT COUNT(*) FROM diagnostic_reports d 
        LEFT JOIN patients p ON d.patient_id = p.id 
        WHERE p.id IS NULL
    """)
    orphaned = cur.fetchone()[0]
    print(f"Orphaned diagnostic reports (no patient): {orphaned}")

    return counts

def load_fhir_data(db_config):
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Track counts for validation
    processed_counts = {
        'Patient': 0,
        'Encounter': 0,
        'Condition': 0,
        'DiagnosticReport': 0,
        'DocumentReference': 0,
        'Claim': 0,
        'ExplanationOfBenefit': 0
    }

    total_files = len(list(glob.glob('synthea/output/fhir/*.json')))
    print(f"Found {total_files} FHIR bundle files to process")
    
    # Process each FHIR bundle file
    for i, file_path in enumerate(glob.glob('synthea/output/fhir/*.json'), 1):
        print(f"\nProcessing file {i}/{total_files}: {file_path}")
        
        with open(file_path) as f:
            bundle = json.load(f)

        file_counts = {k: 0 for k in processed_counts.keys()}
        
        # Process each entry in the bundle
        for entry in bundle['entry']:
            resource = entry['resource']
            resource_type = resource['resourceType']
            
            if resource_type in processed_counts:
                file_counts[resource_type] += 1
                processed_counts[resource_type] += 1

            if resource_type == 'Patient':
                # Insert patient
                cur.execute("""
                    INSERT INTO patients (id, resource_id, gender, birth_date, deceased_date, marital_status, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    resource.get('identifier', [{}])[0].get('value'),
                    resource.get('gender'),
                    resource.get('birthDate'),
                    parse_fhir_datetime(resource.get('deceasedDateTime')),
                    Json(resource.get('maritalStatus', {})),
                    Json(resource)
                ))

            elif resource_type == 'Encounter':
                # Insert encounter
                cur.execute("""
                    INSERT INTO encounters (id, patient_id, status, class, type, period_start, period_end, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['subject']['reference'].split('/')[-1])),
                    resource.get('status'),
                    Json(resource.get('class', {})),
                    Json(resource.get('type', [{}])[0]),
                    parse_fhir_datetime(resource.get('period', {}).get('start')),
                    parse_fhir_datetime(resource.get('period', {}).get('end')),
                    Json(resource)
                ))

            elif resource_type == 'Condition':
                # Insert condition
                cur.execute("""
                    INSERT INTO conditions (id, patient_id, encounter_id, code, clinical_status, verification_status, 
                                         onset_date, abatement_date, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['subject']['reference'].split('/')[-1])),
                    str(uuid.UUID(resource.get('encounter', {}).get('reference', '').split('/')[-1])) if resource.get('encounter') else None,
                    Json(resource.get('code', {})),
                    Json(resource.get('clinicalStatus', {})),
                    Json(resource.get('verificationStatus', {})),
                    parse_fhir_datetime(resource.get('onsetDateTime')),
                    parse_fhir_datetime(resource.get('abatementDateTime')),
                    Json(resource)
                ))

            elif resource_type == 'DiagnosticReport':
                # Insert diagnostic report
                cur.execute("""
                    INSERT INTO diagnostic_reports (id, patient_id, encounter_id, status, effective_date, issued, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['subject']['reference'].split('/')[-1])),
                    str(uuid.UUID(resource.get('encounter', {}).get('reference', '').split('/')[-1])) if resource.get('encounter') else None,
                    resource.get('status'),
                    parse_fhir_datetime(resource.get('effectiveDateTime')),
                    parse_fhir_datetime(resource.get('issued')),
                    Json(resource)
                ))

            elif resource_type == 'DocumentReference':
                # Insert document reference
                cur.execute("""
                    INSERT INTO document_references (id, patient_id, encounter_id, status, type, date, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['subject']['reference'].split('/')[-1])),
                    str(uuid.UUID(resource.get('context', {}).get('encounter', [{}])[0].get('reference', '').split('/')[-1])) if resource.get('context', {}).get('encounter') else None,
                    resource.get('status'),
                    Json(resource.get('type', {})),
                    parse_fhir_datetime(resource.get('date')),
                    Json(resource)
                ))

            elif resource_type == 'Claim':
                # Insert claim
                cur.execute("""
                    INSERT INTO claims (id, patient_id, status, type, use, billable_period_start, billable_period_end, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['patient']['reference'].split('/')[-1])),
                    resource.get('status'),
                    Json(resource.get('type', {})),
                    resource.get('use'),
                    parse_fhir_datetime(resource.get('billablePeriod', {}).get('start')),
                    parse_fhir_datetime(resource.get('billablePeriod', {}).get('end')),
                    Json(resource)
                ))

            elif resource_type == 'ExplanationOfBenefit':
                # Insert explanation of benefit
                cur.execute("""
                    INSERT INTO explanations_of_benefit (id, patient_id, claim_id, status, type, use, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(uuid.UUID(resource['id'])),
                    str(uuid.UUID(resource['patient']['reference'].split('/')[-1])),
                    str(uuid.UUID(resource.get('claim', {}).get('reference', '').split('/')[-1])) if resource.get('claim') else None,
                    resource.get('status'),
                    Json(resource.get('type', {})),
                    resource.get('use'),
                    Json(resource)
                ))

        print(f"File resources processed:", ", ".join(f"{k}: {v}" for k, v in file_counts.items() if v > 0))
        conn.commit()

    print("\nTotal resources processed:")
    for resource_type, count in processed_counts.items():
        print(f"{resource_type}: {count:,}")

    print("\nValidating database contents...")
    db_counts = validate_data_load(cur)

    # Compare processed counts with database counts
    print("\nValidation Summary:")
    print("-" * 50)
    mismatches = []
    if processed_counts['Patient'] != db_counts['patients']:
        mismatches.append(f"Patients: Processed {processed_counts['Patient']:,} vs Stored {db_counts['patients']:,}")
    if processed_counts['Encounter'] != db_counts['encounters']:
        mismatches.append(f"Encounters: Processed {processed_counts['Encounter']:,} vs Stored {db_counts['encounters']:,}")
    if processed_counts['Condition'] != db_counts['conditions']:
        mismatches.append(f"Conditions: Processed {processed_counts['Condition']:,} vs Stored {db_counts['conditions']:,}")
    
    if mismatches:
        print("\nWarning: Found count mismatches:")
        for mismatch in mismatches:
            print(f"- {mismatch}")
    else:
        print("All record counts match successfully!")

    cur.close()
    conn.close()

if __name__ == '__main__':
    db_config = {
        'dbname': 'fhir_db',
        'user': 'fhir_user',
        'password': 'fhir',
        'host': 'localhost'
    }
    
    try:
        print("Starting FHIR data load process...")
        load_fhir_data(db_config)
        print("\nData load completed successfully!")
    except Exception as e:
        print(f"\nError during data load: {str(e)}")
        raise 