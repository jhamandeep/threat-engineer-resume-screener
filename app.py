
import streamlit as st
from docx import Document
import pandas as pd
import re

st.set_page_config(page_title="AI Resume Scorer", layout="wide")

# Sample keyword maps for categories
keyword_map = {
    "Core Skills Match": ["SkyHigh", "Trellix", "McAfee", "DMZ", "SIEM", "Sentinel", "QRadar", "EDR"],
    "Tools & Technologies": ["Python", "PowerShell", "Splunk", "TLS", "Shell", "VPN", "KQL"],
    "Certifications & Education": ["CISSP", "CEH", "CCNA", "B.Tech", "MCA", "Bachelor", "Master"],
    "Soft Skills / Management": ["led", "mentored", "collaborated", "trained", "stakeholder", "presented", "communication"],
    "Achievements / Projects": ["successfully", "achieved", "delivered", "implemented", "completed", "%", "$", "ROI"],
}

structure_sections = ["summary", "experience", "education", "skills", "projects"]

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

def score_resume(text, candidate_name):
    category_scores = {
        "Candidate": candidate_name,
        "Core Skills Match": 0,
        "Tools & Technologies": 0,
        "Certifications & Education": 0,
        "Soft Skills / Management": 0,
        "Achievements / Projects": 0,
        "Resume Clarity & Structure": 0
    }

    text_lower = text.lower()
    # Keyword scoring
    for category, keywords in keyword_map.items():
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        category_scores[category] = min(count * 2, 30 if category == "Core Skills Match" else 15)

    # Structure check
    matched_sections = sum(1 for sec in structure_sections if sec in text_lower)
    category_scores["Resume Clarity & Structure"] = min(matched_sections, 5)

    # Total scoring
    total = (
        category_scores["Core Skills Match"] * 0.25 +
        category_scores["Tools & Technologies"] * 0.20 +
        category_scores["Certifications & Education"] * 0.15 +
        category_scores["Soft Skills / Management"] * 0.15 +
        category_scores["Achievements / Projects"] * 0.15 +
        category_scores["Resume Clarity & Structure"] * 0.10
    )
    category_scores["Total Score"] = round(total, 2)
    return category_scores

# Streamlit UI
st.title("🧠 AI Resume Scorer for Threat Engineer Role")

uploaded_files = st.file_uploader("Upload candidate resumes (DOCX)", type=["docx"], accept_multiple_files=True)
results = []

if uploaded_files:
    for file in uploaded_files:
        candidate_name = file.name.replace(".docx", "").replace("_", " ")
        text = extract_text_from_docx(file)
        result = score_resume(text, candidate_name)
        results.append(result)

    if results:
        df = pd.DataFrame(results)
        df["Rank"] = df["Total Score"].rank(ascending=False, method="min").astype(int)
        df = df.sort_values("Rank")
        st.subheader("📊 Resume Scoring Result")
        st.dataframe(df)

        # Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download as CSV", csv, "resume_scores.csv", "text/csv")
else:
    st.info("Please upload one or more .docx resumes to analyze.")
