#!/usr/bin/env python3

import base64
import glob
import os
import uuid
from fhir_utils import create_library, create_measure, post_resource, evaluate_measure, evaluate_measure_list
from dp_utils import add_laplace_noise

def generate_report(directory, base_url, subject_type, report_type, epsilon, total_epsilon):
    """Generate a report for all .cql files in the directory with composability accounting."""
    results = {}
    total_epsilon_used = 0.0

    # Iterate over .cql files in the directory
    for file_path in glob.glob(os.path.join(directory, "*.cql")):
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            print(f"Processing {filename}...")

            # Check if remaining epsilon budget allows this query
            if total_epsilon_used + epsilon > total_epsilon:
                print(f"Skipping {filename}: Exceeds total epsilon budget ({total_epsilon_used + epsilon} > {total_epsilon})")
                results[filename] = {"error": "Exceeded total epsilon budget", "epsilonUsed": 0.0}
                continue

            try:
                # Read and encode CQL file
                with open(file_path, "rb") as f:
                    cql_data = base64.b64encode(f.read()).decode("utf-8")

                # Generate UUIDs
                library_uri = str(uuid.uuid4()).lower()
                measure_uri = str(uuid.uuid4()).lower()

                # Create and post Library resource
                library_resource = create_library(library_uri, cql_data)
                post_resource(base_url, "Library", library_resource)

                # Create and post Measure resource
                measure_resource = create_measure(measure_uri, library_uri, subject_type)
                measure_response = post_resource(base_url, "Measure", measure_resource)
                measure_id = measure_response.get("id")

                # Evaluate measure
                if report_type == "subject-list":
                    print(f"Generating a report including the list of matching {subject_type.lower()}s for {filename}...")
                    measure_report = evaluate_measure_list(base_url, measure_id)
                    count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                    count_with_dp = add_laplace_noise(count, epsilon)
                    list_reference = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("subjectResults", {}).get("reference", None)
                    results[filename] = {
                        "count": count,
                        "countWithDP": count_with_dp,
                        "listReference": list_reference,
                        "epsilonUsed": epsilon
                    }
                else:
                    print(f"Generating a population count report for {filename}...")
                    measure_report = evaluate_measure(base_url, measure_id)
                    count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                    count_with_dp = add_laplace_noise(count, epsilon)
                    results[filename] = {
                        "count": count,
                        "countWithDP": count_with_dp,
                        "epsilonUsed": epsilon
                    }

                # Update total epsilon used
                total_epsilon_used += epsilon

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                results[filename] = {"error": str(e), "epsilonUsed": 0.0}

    # Add total epsilon used to results
    results["totalEpsilonUsed"] = total_epsilon_used
    return results