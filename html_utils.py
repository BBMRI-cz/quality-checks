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
.stratum {{ margin-left: 20px; margin-top: 10px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc; }}
.stratum-header {{ font-weight: bold; font-size: 1em; margin-bottom: 5px; }}
</style>
</head>
<body>
<h1>Data Quality Check Report</h1>
        <h2>Total Patients: {total_patients} | Total Epsilon Used: {total_epsilon:.2f}</h2>
        """

    for qc_name, qc_data in qc_results.items():
        if qc_name == "totalEpsilonUsed":
            continue

        description = qc_data.get("description", "")
        epsilon = qc_data.get("epsilonUsed", 0)

        # Handle stratified results (e.g., SurvivalRateCheck)
        if "stratified" in qc_data:
            count_alive = qc_data.get("countAlive", 0)
            count_total = qc_data.get("countTotal", 0)
            rate = qc_data.get("rate", 0.0)
            count_alive_dp = qc_data.get("countAliveWithDP", 0)
            rate_dp = qc_data.get("rateWithDP", 0.0)
            percentage = (count_alive / total_patients) * 100 if total_patients else 0
            percentage_dp = (count_alive_dp / total_patients) * 100 if total_patients else 0
            color = get_color(percentage_dp)

            html += f"""
                <div class="qc-block" style="background-color:{color};">
                <div class="header">{qc_name}</div>
                {"<div class='description'>" + description + "</div>" if description else ""}
                <div>Alive Count: {count_alive} (Total: {count_total}, Rate: {rate:.2%})</div>
                <div>Alive Count with Differential Privacy: {count_alive_dp} (Rate: {rate_dp:.2%})</div>
                <div>Epsilon Used: {epsilon}</div>
                """

            # Stratified results
            for stratum_name, stratum_data in qc_data["stratified"].items():
                stratum_count_alive = stratum_data.get("countAlive", 0)
                stratum_count_total = stratum_data.get("countTotal", 0)
                stratum_rate = stratum_data.get("rate", 0.0)
                stratum_count_alive_dp = stratum_data.get("countAliveWithDP", 0)
                stratum_rate_dp = stratum_data.get("rateWithDP", 0.0)
                stratum_percentage = (stratum_count_alive / total_patients) * 100 if total_patients else 0
                stratum_color = get_color(stratum_percentage)

                html += f"""
                    <div class="stratum" style="background-color:{stratum_color};">
                    <div class="stratum-header">{stratum_name.capitalize()}</div>
                    <div>Alive Count: {stratum_count_alive} (Total: {stratum_count_total}, Rate: {stratum_rate:.2%})</div>
                    <div>Alive Count with Differential Privacy: {stratum_count_alive_dp} (Rate: {stratum_rate_dp:.2%})</div>
</div>
                    """
            html += "</div>"

        # Handle non-stratified results
        else:
            count = qc_data.get("count", 0)
            count_dp = qc_data.get("countWithDP", 0)
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