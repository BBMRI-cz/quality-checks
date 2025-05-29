#!/usr/bin/env python3

import json

import html_utils
from cli_utils import parse_args
from report_utils import get_qc_results

def main():
    # Parse command-line arguments
    args = parse_args()

    # Generate report with composability accounting
    results = get_qc_results(args.directory, args.base, args.subject_type, args.report_type, args.epsilon, args.total_epsilon)
    html_utils.save_html_report(qc_results=results, total_patients=1000, filename="qc_report.html")

    # Output results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()