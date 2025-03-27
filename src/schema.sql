-- Core tables for primary FHIR resources

CREATE TABLE patients (
    id UUID PRIMARY KEY,
    resource_id VARCHAR(64),
    gender VARCHAR(10),
    birth_date DATE,
    deceased_date TIMESTAMP,
    marital_status JSONB,
    data JSONB  -- Full FHIR resource
);

CREATE TABLE encounters (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    status VARCHAR(50),
    class JSONB,
    type JSONB,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    data JSONB
);

CREATE TABLE conditions (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    encounter_id UUID REFERENCES encounters(id),
    code JSONB,
    clinical_status JSONB,
    verification_status JSONB,
    onset_date TIMESTAMP,
    abatement_date TIMESTAMP,
    data JSONB
);

CREATE TABLE diagnostic_reports (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    encounter_id UUID REFERENCES encounters(id),
    status VARCHAR(50),
    effective_date TIMESTAMP,
    issued TIMESTAMP,
    data JSONB
);

CREATE TABLE document_references (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    encounter_id UUID REFERENCES encounters(id),
    status VARCHAR(50),
    type JSONB,
    date TIMESTAMP,
    data JSONB
);

CREATE TABLE claims (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    status VARCHAR(50),
    type JSONB,
    use VARCHAR(50),
    billable_period_start TIMESTAMP,
    billable_period_end TIMESTAMP,
    data JSONB
);

CREATE TABLE explanations_of_benefit (
    id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(id),
    claim_id UUID REFERENCES claims(id),
    status VARCHAR(50),
    type JSONB,
    use VARCHAR(50),
    data JSONB
);

-- Create indexes for common query patterns
CREATE INDEX idx_patient_gender ON patients(gender);
CREATE INDEX idx_patient_birth_date ON patients(birth_date);
CREATE INDEX idx_encounter_period ON encounters(period_start, period_end);
CREATE INDEX idx_condition_onset ON conditions(onset_date);