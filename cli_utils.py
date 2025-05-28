#!/usr/bin/env python3

import argparse

def parse_args():
    """Parse command-line arguments."""
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

    return args