// Checks for birth dates before 1900 or in the future
library BirthDateCheck version '1.0.0'
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

context Patient

define CurrentDate: @2025-05-27

define InInitialPopulation:
  exists [Patient] P
    where P.birthDate < @1900-01-01
      or P.birthDate > CurrentDate