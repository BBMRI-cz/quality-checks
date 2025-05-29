library PatientsUpdatedIn2025 version '1.0.0'
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

context Patient

define InInitialPopulation:
    Patient.meta.lastUpdated before @2026-01-01T00:00:00Z