#!/usr/bin/env bash

# Usage: ./evaluate-measures.sh -d <directory> [ -t subject-type ] [ -r report-type ] [ -e epsilon ] <server-base>

# Takes all .cql files in a directory, creates a Library resource from each,
# references them from Measure resources, calls $evaluate-measure, and outputs results as JSON {filename: {count, countWithDP, [listReference]}}.

library() {
cat <<END
{
  "resourceType": "Library",
  "status": "active",
  "type" : {
    "coding" : [
      {
        "system": "http://terminology.hl7.org/CodeSystem/library-type",
        "code" : "logic-library"
      }
    ]
  },
  "content": [
    {
      "contentType": "text/cql"
    }
  ]
}
END
}

measure() {
cat <<END
{
  "resourceType": "Measure",
  "status": "active",
  "subjectCodeableConcept": {
    "coding": [
      {
        "system": "http://hl7.org/fhir/resource-types",
        "code": "Patient"
      }
    ]
  },
  "scoring": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/measure-scoring",
        "code": "cohort"
      }
    ]
  },
  "group": [
    {
      "population": [
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "initial-population"
              }
            ]
          },
          "criteria": {
            "language": "text/cql-identifier",
            "expression": "InInitialPopulation"
          }
        }
      ]
    }
  ]
}
END
}

create-library() {
  library | jq -cM ".url = \"urn:uuid:$1\" | .content[0].data = \"$2\""
}

create-measure() {
  measure | jq -cM ".url = \"urn:uuid:$1\" | .library[0] = \"urn:uuid:$2\" | .subjectCodeableConcept.coding[0].code = \"$3\""
}

post() {
  curl -sH "Content-Type: application/fhir+json" -d @- "$BASE/$1"
}

evaluate-measure() {
  curl -s "$BASE/Measure/$1/\$evaluate-measure?periodStart=2000&periodEnd=2030"
}

evaluate-measure-list() {
  curl -sd '{"resourceType": "Parameters", "parameter": [{"name": "periodStart", "valueDate": "2000"}, {"name": "periodEnd", "valueDate": "2030"}, {"name": "reportType", "valueCode": "subject-list"}]}' \
    -H "Content-Type: application/fhir+json" "$BASE/Measure/$1/\$evaluate-measure"
}

# Function to add Laplace noise for differential privacy
add_laplace_noise() {
  local count=$1
  local epsilon=$2
  # Sensitivity for a count query is 1
  local sensitivity=1
  # Scale parameter for Laplace distribution: sensitivity / epsilon
  local scale=$(echo "$sensitivity / $epsilon" | bc -l)
  # Use Python to generate Laplace noise and add it to the count
  local noisy_count=$(python3 -c "
import numpy as np
count = $count
scale = $scale
noise = np.random.laplace(0, scale)
noisy_count = max(0, round(count + noise))  # Ensure non-negative and round
print(noisy_count)
" | tr -d '\n')
  echo $noisy_count
}

usage()
{
  echo "Usage: $0 -d DIRECTORY [ -t subject-type ] [ -r report-type ] [ -e epsilon ] BASE"
  echo ""
  echo "Example subject-types: Patient, Specimen; default is Patient"
  echo "Possible report-types: subject-list, population; default is population"
  echo "Epsilon: differential privacy parameter; default is 1.0"
  exit 2
}

unset DIRECTORY SUBJECT_TYPE REPORT_TYPE EPSILON BASE

while getopts 'd:t:r:e:' c
do
  case ${c} in
    d) DIRECTORY=$OPTARG ;;
    t) SUBJECT_TYPE=$OPTARG ;;
    r) REPORT_TYPE=$OPTARG ;;
    e) EPSILON=$OPTARG ;;
  esac
done

shift $((OPTIND-1))
BASE=$1

[[ -z "$DIRECTORY" ]] && usage
[[ -z "$SUBJECT_TYPE" ]] && SUBJECT_TYPE="Patient"
[[ -z "$EPSILON" ]] && EPSILON="1.0"
[[ -z "$BASE" ]] && usage

SUBJECT_TYPE_LOWER=$(echo $SUBJECT_TYPE | tr '[:upper:]' '[:lower:]')

# Initialize JSON output
RESULTS="{}"

# Iterate over all .cql files in the directory
for FILE in "$DIRECTORY"/*.cql; do
  if [[ -f "$FILE" ]]; then
    FILENAME=$(basename "$FILE")
    DATA=$(base64 < "$FILE" | tr -d '\n')
    LIBRARY_URI=$(uuidgen | tr '[:upper:]' '[:lower:]')
    MEASURE_URI=$(uuidgen | tr '[:upper:]' '[:lower:]')

    create-library ${LIBRARY_URI} ${DATA} | post "Library" > /dev/null

    MEASURE_ID=$(create-measure ${MEASURE_URI} ${LIBRARY_URI} ${SUBJECT_TYPE} | post "Measure" | jq -r .id | tr -d '\r')

    if [ "subject-list" = "$REPORT_TYPE" ]; then
      echo "Generating a report including the list of matching ${SUBJECT_TYPE_LOWER}s for $FILENAME..."
      MEASURE_REPORT=$(evaluate-measure-list ${MEASURE_ID})
      COUNT=$(echo $MEASURE_REPORT | jq -r '.group[0].population[0].count // 0' | tr -d '\r')
      COUNT_WITH_DP=$(add_laplace_noise $COUNT $EPSILON)
      LIST_REFERENCE=$(echo $MEASURE_REPORT | jq -r '.group[0].population[0].subjectResults.reference // ""' | tr -d '\r')
      if [ -n "$LIST_REFERENCE" ]; then
        LIST_ID=$(echo $LIST_REFERENCE | cut -d '/' -f2)
        RESULT="{\"count\": $COUNT, \"countWithDP\": $COUNT_WITH_DP, \"listReference\": \"$LIST_REFERENCE\"}"
      else
        RESULT="{\"count\": $COUNT, \"countWithDP\": $COUNT_WITH_DP, \"listReference\": null}"
      fi
    else
      echo "Generating a population count report for $FILENAME..."
      MEASURE_REPORT=$(evaluate-measure ${MEASURE_ID})
      COUNT=$(echo $MEASURE_REPORT | jq -r '.group[0].population[0].count // 0' | tr -d '\r')
      COUNT_WITH_DP=$(add_laplace_noise $COUNT $EPSILON)
      RESULT="{\"count\": $COUNT, \"countWithDP\": $COUNT_WITH_DP}"
    fi

    # Add result to JSON output
    RESULTS=$(echo $RESULTS | jq --arg fname "$FILENAME" --argjson res "$RESULT" '. + {($fname): $res}')
  fi
done

# Output the final JSON results
echo $RESULTS | jq .