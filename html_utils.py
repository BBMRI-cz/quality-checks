def save_html_report(qc_results: dict, total_patients: int, filename: str):
    html_content = generate_html_report(qc_results, total_patients)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Report saved to {filename}")


def generate_html_report(qc_results: dict, total_patients: int) -> str:
    def get_color(percentage):
        if percentage > 10:
            return "#ffcccc"  # light red
        elif percentage > 1:
            return "#fff2cc"  # light yellow
        else:
            return "#ccffcc"  # light green

    total_epsilon = qc_results.get("totalEpsilonUsed", 0)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Data Quality Check Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
h1 {{ color: #333; margin-bottom: 5px; }}
h2 {{ color: #555; margin-top: 0; margin-bottom: 20px; font-weight: normal; }}
.qc-block {{ border-radius: 5px; margin-bottom: 15px; padding: 15px; background-color: #eee; }}
.description {{ font-style: italic; color: #555; margin-bottom: 10px; }}
.header {{ font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }}
</style>
</head>
<body>
<h1>Data Quality Check Report</h1>
        <h2>Total Patients: {total_patients} | Total Epsilon Used: {total_epsilon:.2f}</h2>
        """

    for qc_name, qc_data in qc_results.items():
        if qc_name == "totalEpsilonUsed":
            continue

        count = qc_data.get("count", 0)
        count_dp = qc_data.get("countWithDP", 0)
        epsilon = qc_data.get("epsilonUsed", 0)
        description = qc_data.get("description", "")
        percentage = (count / total_patients) * 100 if total_patients else 0
        percentage_dp = (count_dp / total_patients) * 100 if total_patients else 0
        color = get_color(percentage_dp)

        html += f"""
            <div class="qc-block" style="background-color:{color};">
            <div class="header">{qc_name}</div>
            {"<div class='description'>" + description + "</div>" if description else ""}
            <div>Count: {count} ({percentage:.2f}%)</div>
            <div>Count with Differential Privacy: {count_dp} ({percentage_dp:.2f}%)</div>
            <div>Epsilon Used: {epsilon}</div>
</div>
            """

    html += """
</body>
</html>
    """
    return html

