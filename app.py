
import streamlit as st
import pandas as pd

# Set page config
st.set_page_config(page_title="Threat Engineer Verdict Engine", layout="wide")

# Define scoring rules
scoring_rules = {
    "✔": 5,
    "⚠": 3,
    "✘": 0
}

# Scoring function
def symbol_to_score(cell):
    if isinstance(cell, str):
        if "✔" in cell:
            return scoring_rules["✔"]
        elif "⚠" in cell:
            return scoring_rules["⚠"]
        elif "✘" in cell:
            return scoring_rules["✘"]
    return 0

# Upload Excel
st.title("📊 Threat Engineer Candidate Verdict Engine")
uploaded_file = st.file_uploader("Upload Candidate Comparison Sheet (Excel)", type=["xlsx"])

if uploaded_file:
    raw_df = pd.read_excel(uploaded_file)
    st.success("✅ File uploaded and parsed")

    # Get core dimensions (excluding Candidate and Remarks)
    dim_cols = [col for col in raw_df.columns if col not in ["Candidate", "Detailed Remarks"]]

    # Compute scores
    scored_df = raw_df.copy()
    for col in dim_cols:
        scored_df[f"{col} Score"] = scored_df[col].apply(symbol_to_score)

    score_cols = [f"{col} Score" for col in dim_cols]
    scored_df["Total Score"] = scored_df[score_cols].sum(axis=1)
    scored_df["Max Score"] = len(score_cols) * scoring_rules["✔"]
    scored_df["Fit %"] = round((scored_df["Total Score"] / scored_df["Max Score"]) * 100, 2)

    def verdict(score):
        if score >= 80:
            return "✅ Strong Fit"
        elif score >= 60:
            return "⚠️ Partial Fit"
        else:
            return "❌ Low Fit"

    scored_df["Final Verdict"] = scored_df["Fit %"].apply(verdict)

    st.subheader("📋 Candidate Verdict Table")
    st.dataframe(scored_df[["Candidate", "Fit %", "Final Verdict", "Detailed Remarks"]])

    st.subheader("📑 Full Score Breakdown")
    st.dataframe(scored_df)
else:
    st.info("Please upload a structured Excel with ✅, ⚠, and ✘ symbols to proceed.")
