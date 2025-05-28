#!/usr/bin/env python3

import json
from cli_utils import parse_args
from report_utils import generate_report

def main():
    # Parse command-line arguments
    args = parse_args()

    # Generate report
    results = generate_report(args.directory, args.base, args.subject_type, args.report_type, args.epsilon)

    # Output results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()