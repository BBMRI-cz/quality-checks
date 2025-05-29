// How many patients have the Gender attribute
library GenderPresenceCheck version '1.0.0'
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

context Patient

define HasGender:
   not Patient.gender.exists()

define InInitialPopulation:
  HasGender
