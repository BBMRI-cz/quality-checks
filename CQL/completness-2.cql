// How many patients do not have a diagnosis
library PatientConditionChecks version '1.0.0'

using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

context Patient

// Patients who do not have any Condition resources linked to them
define HasNoCondition:
  not exists (
    [Condition] C
      where C.subject.reference = 'Patient/' + Patient.id
  )

// Patients who have at least one Condition, but the code is missing
define HasConditionWithNoCode:
  exists (
    [Condition] C
      where C.subject.reference = 'Patient/' + Patient.id
        and C.code is null
  )

// Main expression required by engine
define InInitialPopulation:
  HasNoCondition or HasConditionWithNoCode
