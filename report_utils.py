#!/usr/bin/env python3

import base64
import glob
import json
import os
import uuid
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from dateutil.parser import parse as parse_date
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import icd10
from fhir_utils import create_library, create_measure, post_resource, evaluate_measure, evaluate_measure_list
from dp_utils import add_laplace_noise

class QualityCheck(ABC):
    """Base class for quality checks (CQL or Python-based)."""
    def __init__(self, name, description="Unknown", epsilon=1.0):
        self.name = name
        self.epsilon = epsilon
        self.description = description

    def _fetch_all_resources(self, base_url, resource_type, elements):
        """Fetch all resources with pagination and retries."""
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        resources = []
        url = f"{base_url}/{resource_type}?_count=100&_elements={','.join(elements)}"
        while url:
            response = session.get(url)
            response.raise_for_status()
            bundle = response.json()
            resources.extend(bundle.get("entry", []))
            next_link = next((link["url"] for link in bundle.get("link", []) if link["relation"] == "next"), None)
            url = next_link
        return resources

    @abstractmethod
    def execute(self, base_url, subject_type, report_type):
        """Execute the check and return results."""
        pass

    def get_description(self):
        return self.description

class CQLQualityCheck(QualityCheck):
    """Quality check using a CQL file."""
    def __init__(self, filename, cql_path, epsilon=1.0):
        super().__init__(filename, epsilon=epsilon)
        self.cql_path = cql_path

    def execute(self, base_url, subject_type, report_type):
        try:
            with open(self.cql_path, "r") as f:
                first_line = f.readline().strip()
                if first_line.startswith("//"):
                    comment_text = first_line[2:].strip()
                    self.description = comment_text
            with open(self.cql_path, "rb") as f:
                cql_data = base64.b64encode(f.read()).decode("utf-8")

            library_uri = str(uuid.uuid4()).lower()
            measure_uri = str(uuid.uuid4()).lower()

            library_resource = create_library(library_uri, cql_data)
            post_resource(base_url, "Library", library_resource)

            measure_resource = create_measure(measure_uri, library_uri, subject_type)
            measure_response = post_resource(base_url, "Measure", measure_resource)
            measure_id = measure_response.get("id")

            if report_type == "subject-list":
                print(f"Generating a report including the list of matching {subject_type.lower()}s for {self.name}...")
                measure_report = evaluate_measure_list(base_url, measure_id)
                count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                list_reference = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("subjectResults", {}).get("reference", None)
                patient_ids = []
                if list_reference:
                    list_response = requests.get(f"{base_url}/{list_reference}").json()
                    patient_ids = [entry.get("item", {}).get("reference", "") for entry in list_response.get("entry", [])]
                    #print(f"Matched patient IDs for {self.name}: {patient_ids}")
                return {
                    "count": count,
                    "countWithDP": add_laplace_noise(count, self.epsilon),
                    "listReference": list_reference,
                    "patientIds": patient_ids,
                    "epsilonUsed": self.epsilon
                }
            else:
                measure_report = evaluate_measure(base_url, measure_id)
                count = measure_report.get("group", [{}])[0].get("population", [{}])[0].get("count", 0)
                return {
                    "count": count,
                    "countWithDP": add_laplace_noise(count, self.epsilon),
                    "epsilonUsed": self.epsilon
                }
        except Exception as e:
            print(f"Error processing {self.name}: {e}")
            return {"error": str(e), "epsilonUsed": 0.0}

class DuplicateIdentifierCheck(QualityCheck):
    """Python-based check for duplicate patient identifiers."""
    def __init__(self, identifier_system="https://fhir.bbmri.de/id/patient", epsilon=1.0):
        super().__init__("uniqness-1", "Duplicate patients",epsilon)
        self.identifier_system = identifier_system

    def execute(self, base_url, subject_type, report_type):
        try:
            patients = self._fetch_all_resources(base_url, "Patient", ["id", "identifier"])
            identifier_map = {}
            for entry in patients:
                patient = entry.get("resource", {})
                patient_id = patient.get("id")
                identifiers = patient.get("identifier", [])
                for ident in identifiers:
                    if ident.get("system") == self.identifier_system:
                        ident_value = ident.get("value")
                        if ident_value:
                            if ident_value not in identifier_map:
                                identifier_map[ident_value] = []
                            identifier_map[ident_value].append(f"Patient/{patient_id}")

            duplicate_ids = []
            for ident_value, patient_refs in identifier_map.items():
                if len(patient_refs) > 1:
                    duplicate_ids.extend(patient_refs)

            count = len(set(duplicate_ids))
            result = {
                "count": count,
                "countWithDP": add_laplace_noise(count, self.epsilon),
                "epsilonUsed": self.epsilon
            }
            if report_type == "subject-list":
                result["patientIds"] = list(set(duplicate_ids))
                #print(f"Duplicate patient IDs for {self.name}: {result['patientIds']}")
            return result
        except Exception as e:
            print(f"Error processing {self.name}: {e}")
            return {"error": str(e), "epsilonUsed": 0.0}

class InvalidConditionICDCheck(QualityCheck):
    """Check for invalid ICD-10 or ICD-9 codes in Condition.code."""
    def __init__(self, epsilon=1.0):
        super().__init__("validity-1", "How many conditions have invalid ICD-10 codes",epsilon)

    def execute(self, base_url, subject_type, report_type):
        try:
            conditions = self._fetch_all_resources(base_url, "Condition", ["id", "code", "subject"])
            invalid_ids = []
            for entry in conditions:
                condition = entry.get("resource", {})
                code = condition.get("code", {})
                codings = code.get("coding", [])
                has_valid_icd = False
                for coding in codings:
                    system = coding.get("system")
                    code_value = coding.get("code")
                    if system in ["http://hl7.org/fhir/sid/icd-10", "http://hl7.org/fhir/sid/icd-10-cm"]:
                        if code_value and icd10.find(code_value):
                            has_valid_icd = True
                            break
                    elif system == "http://hl7.org/fhir/sid/icd-9-cm":
                        # Basic ICD-9 validation (3-5 digits, optional decimal)
                        if code_value and re.match(r'^\d{3}(\.\d{1,2})?$', code_value):
                            has_valid_icd = True
                            break
                if codings and not has_valid_icd:
                    subject_ref = condition.get("subject", {}).get("reference")
                    if subject_ref:
                        invalid_ids.append(subject_ref)

            count = len(set(invalid_ids))
            result = {
                "count": count,
                "countWithDP": add_laplace_noise(count, self.epsilon),
                "epsilonUsed": self.epsilon
            }
            if report_type == "subject-list":
                result["patientIds"] = "[]"
                #print(f"Patients with invalid Condition ICD codes for {self.name}: {result['patientIds']}")
            return result
        except Exception as e:
            print(f"Error processing {self.name}: {e}")
            return {"error": str(e), "epsilonUsed": 0.0}

class InvalidSpecimenICDCheck(QualityCheck):
    """Check for invalid ICD-10 or ICD-9 codes in Specimen SampleDiagnosis extension."""
    def __init__(self, epsilon=1.0):
        super().__init__("validity-2", "How many Specimens have invalid ICD-10 diagnoses" ,epsilon)
        self.extension_url = "https://fhir.bbmri.de/StructureDefinition/SampleDiagnosis"

    def execute(self, base_url, subject_type, report_type):
        try:
            specimens = self._fetch_all_resources(base_url, "Specimen", ["id", "extension", "subject"])
            invalid_ids = []
            for entry in specimens:
                specimen = entry.get("resource", {})
                extensions = specimen.get("extension", [])
                sample_diagnosis = next((ext for ext in extensions if ext.get("url") == self.extension_url), None)
                if sample_diagnosis:
                    coding = sample_diagnosis.get("valueCodeableConcept", {}).get("coding", [{}])[0]
                    system = coding.get("system")
                    code_value = coding.get("code")
                    is_valid = False
                    if system in ["http://hl7.org/fhir/sid/icd-10", "http://hl7.org/fhir/sid/icd-10-cm"]:
                        if code_value and icd10.find(code_value):
                            is_valid = True
                        # else:
                        #     print(code_value + " is not valid")
                    elif system == "http://hl7.org/fhir/sid/icd-9-cm":
                        if code_value and re.match(r'^\d{3}(\.\d{1,2})?$', code_value):
                            is_valid = True
                    if not is_valid and code_value:
                        subject_ref = specimen.get("subject", {}).get("reference")
                        if subject_ref:
                            invalid_ids.append(subject_ref)

            count = len(set(invalid_ids))
            result = {
                "count": count,
                "countWithDP": add_laplace_noise(count, self.epsilon),
                "epsilonUsed": self.epsilon
            }
            if report_type == "subject-list":
                result["patientIds"] = "[]"
                #print(f"Patients with invalid Specimen ICD codes for {self.name}: {result['patientIds']}")
            return result
        except Exception as e:
            print(f"Error processing {self.name}: {e}")
            return {"error": str(e), "epsilonUsed": 0.0}

class StalePatientCheck(QualityCheck):
    """Check for patients not updated in the last year."""
    def __init__(self, epsilon=1.0):
        super().__init__("timeliness-1", "How many patients were last updated more than a year ago",epsilon)
        self.cutoff_date = parse_date("2024-05-28T00:00:00Z")

    def execute(self, base_url, subject_type, report_type):
        try:
            patients = self._fetch_all_resources(base_url, "Patient", ["id", "meta"])
            stale_ids = []
            for entry in patients:
                patient = entry.get("resource", {})
                last_updated = patient.get("meta", {}).get("lastUpdated")
                if last_updated:
                    last_updated_date = parse_date(last_updated)
                    if last_updated_date < self.cutoff_date:
                        stale_ids.append(f"Patient/{patient.get('id')}")

            # Fallback: Check Condition.recordedDate if no stale patients found
            if not stale_ids:
                conditions = self._fetch_all_resources(base_url, "Condition", ["subject", "recordedDate"])
                for entry in conditions:
                    condition = entry.get("resource", {})
                    recorded_date = condition.get("recordedDate")
                    if recorded_date:
                        recorded_date_obj = parse_date(recorded_date)
                        if recorded_date_obj < self.cutoff_date:
                            subject_ref = condition.get("subject", {}).get("reference")
                            if subject_ref:
                                stale_ids.append(subject_ref)

            count = len(set(stale_ids))
            result = {
                "count": count,
                "countWithDP": add_laplace_noise(count, self.epsilon),
                "epsilonUsed": self.epsilon
            }
            if report_type == "subject-list":
                result["patientIds"] = "[]"
                #print(f"Stale patient IDs for {self.name}: {result['patientIds']}")
            return result
        except Exception as e:
            print(f"Error processing {self.name}: {e}")
            return {"error": str(e), "epsilonUsed": 0.0}

def get_qc_results(directory, base_url, subject_type, report_type, epsilon, total_epsilon):
    """Run all QCs and aggregate their results (CQL and Python-based)."""
    results = {}
    total_epsilon_used = 0.0

    # Register quality checks
    quality_checks = []
    # CQL-based checks
    for file_path in glob.glob(os.path.join(directory, "*.cql")):
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            quality_checks.append(CQLQualityCheck(filename, file_path, epsilon))
    # Python-based checks
    quality_checks.extend([
        DuplicateIdentifierCheck(epsilon=epsilon),
        InvalidConditionICDCheck(epsilon=epsilon),
        InvalidSpecimenICDCheck(epsilon=epsilon),
        StalePatientCheck(epsilon=epsilon)
    ])

    for check in quality_checks:
        if total_epsilon_used + epsilon > total_epsilon:
            print(f"Skipping {check.name}: Exceeds total epsilon budget ({total_epsilon_used + epsilon} > {total_epsilon})")
            results[check.name] = {"error": "Exceeded total epsilon budget", "epsilonUsed": 0.0}
            continue

        result = check.execute(base_url, subject_type, report_type)
        results[check.name] = result
        results[check.name]["description"] = check.get_description()
        total_epsilon_used += result.get("epsilonUsed", 0.0)

    results["totalEpsilonUsed"] = total_epsilon_used
    return results