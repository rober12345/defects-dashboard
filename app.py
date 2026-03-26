from flask import Flask, request, render_template_string
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

app = Flask(__name__)

MAX_OPERATORS = 50
MAX_DEFECTS = 15

HTML = """
<h1>Quality Dashboard</h1>

<form method="POST">

<h2>Define Defects (Max 15)</h2>
{% for i in range(max_defects) %}
<input type="text" name="defect{{i}}" placeholder="Defect {{i+1}}">
{% endfor %}

<h2>Operators & Defects Matrix (Max 50)</h2>
<table border="1" cellpadding="5">
<tr>
    <th>Operator</th>
    {% for i in range(max_defects) %}
    <th>D{{i+1}}</th>
    {% endfor %}
</tr>

{% for i in range(max_operators) %}
<tr>
    <td><input type="text" name="operator{{i}}" placeholder="Operator {{i+1}}"></td>
    
    {% for j in range(max_defects) %}
    <td><input type="number" name="cell_{{i}}_{{j}}" value="0" min="0"></td>
    {% endfor %}
</tr>
{% endfor %}
</table>

<br><br>
<button type="submit">Generate Charts</button>
</form>

{% if pareto %}
<h2>Pareto Chart</h2>
<img src="data:image/png;base64,{{pareto}}"/>

<h2>Stacked Chart</h2>
<img src="data:image/png;base64,{{stacked}}"/>
{% endif %}
"""

# ---------------------------
# CREATE PARETO
# ---------------------------
def create_pareto(df):
    df = df[df["Quantity"] > 0]
    df = df.sort_values(by="Quantity", ascending=False)
    df["Cum %"] = df["Quantity"].cumsum() / df["Quantity"].sum()

    fig, ax1 = plt.subplots()

    ax1.bar(df["Failure"], df["Quantity"])
    ax1.set_ylabel("Quantity")
    ax1.set_xticks(range(len(df["Failure"])))
    ax1.set_xticklabels(df["Failure"], rotation=45, ha='right')

    ax2 = ax1.twinx()
    ax2.plot(range(len(df["Failure"])), df["Cum %"], marker='o')
    ax2.set_ylabel("Cumulative %")

    plt.title("Pareto - Failures")
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()

    return base64.b64encode(img.getvalue()).decode()


# ---------------------------
# CREATE STACKED (UPGRADED)
# ---------------------------
def create_stacked(df):

    # 👉 Sort operators by total defects (worst first)
    df["Total"] = df.drop(columns=["Operator"]).sum(axis=1)
    df = df.sort_values(by="Total", ascending=False)

    df = df.set_index("Operator")

    fig, ax = plt.subplots()

    bottom = None

    for col in df.columns[:-1]:  # exclude Total column
        if df[col].sum() == 0:
            continue

        if bottom is None:
            bars = ax.bar(df.index, df[col], label=col)
            bottom = df[col]
        else:
            bars = ax.bar(df.index, df[col], bottom=bottom, label=col)
            bottom += df[col]

    # 👉 Add totals on top of bars
    for i, total in enumerate(df["Total"]):
        ax.text(i, total + 0.1, str(int(total)), ha='center', fontsize=9)

    ax.set_ylabel("Total Defects")
    ax.set_xlabel("Operator")

    plt.xticks(rotation=45, ha='right')

    # ✅ LEGEND (what you wanted)
    ax.legend(title="Defects", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.title("Defects by Operator")

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()

    return base64.b64encode(img.getvalue()).decode()


# ---------------------------
# MAIN
# ---------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":

        defects = []
        for j in range(MAX_DEFECTS):
            d = request.form.get(f"defect{j}")
            if d:
                defects.append(d)

        data = []
        pareto_dict = {d: 0 for d in defects}

        for i in range(MAX_OPERATORS):
            op = request.form.get(f"operator{i}")
            if not op:
                continue

            row = {"Operator": op}

            for j, defect in enumerate(defects):
                val = request.form.get(f"cell_{i}_{j}")
                qty = int(val) if val else 0
                row[defect] = qty
                pareto_dict[defect] += qty

            data.append(row)

        if not data:
            return render_template_string(HTML, max_operators=MAX_OPERATORS, max_defects=MAX_DEFECTS)

        df = pd.DataFrame(data)

        pareto_df = pd.DataFrame({
            "Failure": list(pareto_dict.keys()),
            "Quantity": list(pareto_dict.values())
        })

        pareto_img = create_pareto(pareto_df)
        stacked_img = create_stacked(df)

        return render_template_string(
            HTML,
            pareto=pareto_img,
            stacked=stacked_img,
            max_operators=MAX_OPERATORS,
            max_defects=MAX_DEFECTS
        )

    return render_template_string(HTML, max_operators=MAX_OPERATORS, max_defects=MAX_DEFECTS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)