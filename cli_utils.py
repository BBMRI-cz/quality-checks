#!/usr/bin/env python3

import argparse

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate CQL measures and output results with differential privacy.",
        usage="%(prog)s -d DIRECTORY [-t subject-type] [-r report-type] [-e epsilon] [-te total-epsilon] BASE"
    )
    parser.add_argument("-d", "--directory", required=True, help="Directory containing .cql files")
    parser.add_argument("-t", "--subject-type", default="Patient", help="Subject type (e.g., Patient, Specimen)")
    parser.add_argument("-r", "--report-type", choices=["population", "subject-list"], default="population",
                        help="Report type: population or subject-list")
    parser.add_argument("-e", "--epsilon", type=float, default=1.0, help="Per-query differential privacy epsilon (default: 1.0)")
    parser.add_argument("-te", "--total-epsilon", type=float, default=10.0, help="Total epsilon budget for all queries (default: 10.0)")
    parser.add_argument("base", help="FHIR server base URL")
    args = parser.parse_args()

    if args.epsilon <= 0:
        parser.error("Epsilon must be positive")
    if args.total_epsilon <= 0:
        parser.error("Total epsilon must be positive")
    if args.epsilon > args.total_epsilon:
        parser.error("Per-query epsilon cannot exceed total epsilon budget")

    return args