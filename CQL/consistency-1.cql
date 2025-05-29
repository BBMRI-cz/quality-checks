// How many patients do not have supported gender value
library UnsupportedGenderPatients version '1.0.0'
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

context Patient

define InInitialPopulation:
  Patient.gender is null
    or Patient.gender !~ 'male'
    and Patient.gender !~ 'female'
    and Patient.gender !~ 'other'
    and Patient.gender !~ 'unknown'