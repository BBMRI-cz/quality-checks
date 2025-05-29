// Checks for incompatible diagnosis with the Gender of the Patient
library "GenderIncompatibleDiagnosis"
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

codesystem icd10: 'http://hl7.org/fhir/sid/icd-10'

// Define specific ICD-10 codes
code "ProstateCancer": 'C61' from icd10
code "CervicalCancer": 'C53.9' from icd10

context Patient

// Define the patient's gender
define PatientGender:
  Patient.gender

// Identify conditions with male-specific diagnoses
define MaleSpecificConditions:
  [Condition: code in "ProstateCancer"] C
    where C.subject.reference = 'Patient/' + Patient.id

// Identify conditions with female-specific diagnoses
define FemaleSpecificConditions:
  [Condition: code in "CervicalCancer"] C
    where C.subject.reference = 'Patient/' + Patient.id

// Check for gender incompatibility
define GenderIncompatibleDiagnosis:
  (PatientGender = 'female' and exists MaleSpecificConditions)
    or (PatientGender = 'male' and exists FemaleSpecificConditions)

// Define the initial population (patients with potential incompatibilities)
define InInitialPopulation:
  exists MaleSpecificConditions
    or exists FemaleSpecificConditions
    or GenderIncompatibleDiagnosis