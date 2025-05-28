#!/usr/bin/env python3

import argparse
import base64
import glob
import json
import os
import requests
import uuid
import numpy as np

def library_template():
    return {
        "resourceType": "Library",
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/library-type",
                    "code": "logic-library"
                }
            ]
        },
        "content": [
            {
                "contentType": "text/cql"
            }
        ]
    }

def measure_template():
    return {
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

def create_library(library_uri, cql_data):
    library = library_template()
    library["url"] = f"urn:uuid:{library_uri}"
    library["content"][0]["data"] = cql_data
    return library

def create_measure(measure_uri, library_uri, subject_type):
    measure = measure_template()
    measure["url"] = f"urn:uuid:{measure_uri}"
    measure["library"] = [f"urn:uuid:{library_uri}"]
    measure["subjectCodeableConcept"]["coding"][0]["code"] = subject_type
    return measure

def post_resource(base_url, resource_type, resource):
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(f"{base_url}/{resource_type}", json=resource, headers=headers)
    response.raise_for_status()
    return response.json()

def evaluate_measure(base_url, measure_id):
    url = f"{base_url}/Measure/{measure_id}/$evaluate-measure?periodStart=2000&periodEnd=2030"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def evaluate_measure_list(base_url, measure_id):
    headers = {"Content-Type": "application/fhir+json"}
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "periodStart", "valueDate": "2000"},
            {"name": "periodEnd", "valueDate": "2030"},
            {"name": "reportType", "valueCode": "subject-list"}
        ]
    }
    response = requests.post(f"{base_url}/Measure/{measure_id}/$evaluate-measure", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def add_laplace_noise(count, epsilon):
    sensitivity = 1  # Sensitivity for a count query
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    noisy_count = max(0, round(count + noise))  # Ensure non-negative and round
    return noisy_count

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate CQL measures and output results with differential privacy.",
        usage="%(prog)s -d DIRECTORY [-t subject-type] [-r report-type] [-e epsilon] BASE"
    )
    parser.add_argument("-d", "--directory", required=True, help="Directory containing .cql files")
    parser.add_argument("-t", "--subject-type", default="Patient", help="Subject type (e.g., Patient, Specimen)")
    parser.add_argument("-r", "--report-type", choices=["population", "subject-list"], default="population",
                        help="Report type: population or subject-list")
    parser.add_argument("-e", "--epsilon", type=float, default=1.0, help="Differential privacy epsilon (default: 1.0)")
    parser.add_argument("base", help="FHIR server base URL")
    args = parser.parse_args()

    if args.epsilon <= 0:
        parser.error("Epsilon must be positive")

    results = {}

    # Iterate over .cql files in the directory
    for file_path in glob.glob(os.path.join(args.directory, "*.cql")):
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            print(f"Processing {filename}...")

            # Read and encode CQL file
            with open(file_path, "rb") as f:
                cql_data = base64.b64encode(f.read()).decode("utf-8")

            # Generate UUIDs
            library_uri = str(uuid.uuid4()).lower()
            measure_uri = str(uuid.uuid4()).lower()

            # Create and post Library resource
            library_resource = create_library(library_uri, cql_data)
            post_resource(args.base, "Library", library_resource)

            # Create and post Measure resource
            measure_resource = create_measure(measure_uri, library_uri, args.subject_type)
            measure_response = post_resource(args.base, "Measure", measure_resource)
            measure_id = measure_response.get("id")

            # Evaluate measure
            if args.report_type == "subject-list":
                print(f"Generating a report including the list of matching {args.subject_type.lower()}s for {filename}...")
                measure_report = evaluate_measure_list(args.base, measure_id)
                count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                count_with_dp = add_laplace_noise(count, args.epsilon)
                list_reference = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("subjectResults", {}).get("reference", None)
                results[filename] = {
                    "count": count,
                    "countWithDP": count_with_dp,
                    "listReference": list_reference
                }
            else:
                print(f"Generating a population count report for {filename}...")
                measure_report = evaluate_measure(args.base, measure_id)
                count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                count_with_dp = add_laplace_noise(count, args.epsilon)
                results[filename] = {
                    "count": count,
                    "countWithDP": count_with_dp
                }

    # Output results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()