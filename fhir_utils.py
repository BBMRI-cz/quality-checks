#!/usr/bin/env python3

import requests

def library_template():
    """Return a FHIR Library resource template."""
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
    """Return a FHIR Measure resource template."""
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
    """Create a FHIR Library resource with the given URI and CQL data."""
    library = library_template()
    library["url"] = f"urn:uuid:{library_uri}"
    library["content"][0]["data"] = cql_data
    return library

def create_measure(measure_uri, library_uri, subject_type):
    """Create a FHIR Measure resource with the given URIs and subject type."""
    measure = measure_template()
    measure["url"] = f"urn:uuid:{measure_uri}"
    measure["library"] = [f"urn:uuid:{library_uri}"]
    measure["subjectCodeableConcept"]["coding"][0]["code"] = subject_type
    return measure

def post_resource(base_url, resource_type, resource):
    """Post a FHIR resource to the server and return the response."""
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(f"{base_url}/{resource_type}", json=resource, headers=headers)
    response.raise_for_status()
    return response.json()

def evaluate_measure(base_url, measure_id):
    """Evaluate a FHIR Measure resource and return the report."""
    url = f"{base_url}/Measure/{measure_id}/$evaluate-measure?periodStart=2000&periodEnd=2030"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def evaluate_measure_list(base_url, measure_id):
    """Evaluate a FHIR Measure resource for a subject list and return the report."""
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