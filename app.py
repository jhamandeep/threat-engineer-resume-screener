
import streamlit as st
st.set_page_config(page_title="Structured Resume Screener", layout="wide")

from docx import Document
import pandas as pd

# --- Helper: Extract text from DOCX ---
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])

# --- Predefined keyword buckets (can be expanded or externalized) ---
keyword_model = {
    "Required": ["SkyHigh", "Trellix", "DMZ", "SIEM", "CCNA", "Threat Engineer", "deployment", "implementation"],
    "Preferred": ["ISO 27001", "SOC2", "PowerShell", "KQL", "TLS", "Splunk", "VPN", "Zero Trust"],
    "Soft Skills": ["communication", "presentation", "stakeholder", "collaboration", "training", "documentation"]
}

weights = {
    "Required": 2.0,
    "Preferred": 1.5,
    "Soft Skills": 1.0
}

# --- Rule-based scorer ---
def structured_score(resume_text, jd_keywords):
    scored = []
    total = 0
    max_score = 0

    for category, keywords in jd_keywords.items():
        matches = []
        for kw in keywords:
            if kw.lower() in resume_text.lower():
                matches.append(kw)
        score = len(matches) * weights[category]
        possible = len(keywords) * weights[category]
        total += score
        max_score += possible
        scored.append((category, len(matches), len(keywords), matches, score, possible))

    final_percent = round((total / max_score) * 100, 2) if max_score else 0
    return scored, final_percent

# --- UI ---
st.title("✅ Structured Resume Screener (Keyword-Based, Transparent)")

# JD Block Editor
st.subheader("📌 JD Keyword Buckets (Editable)")
required_input = st.text_area("Required Keywords", ", ".join(keyword_model["Required"]))
preferred_input = st.text_area("Preferred Keywords", ", ".join(keyword_model["Preferred"]))
soft_input = st.text_area("Soft Skills Keywords", ", ".join(keyword_model["Soft Skills"]))

# Update keyword model
keyword_model["Required"] = [kw.strip() for kw in required_input.split(",") if kw.strip()]
keyword_model["Preferred"] = [kw.strip() for kw in preferred_input.split(",") if kw.strip()]
keyword_model["Soft Skills"] = [kw.strip() for kw in soft_input.split(",") if kw.strip()]

# Resume Upload
st.subheader("📎 Upload Resume (DOCX)")
resume_file = st.file_uploader("Upload Resume File", type=["docx"])
if resume_file:
    resume_text = extract_text_from_docx(resume_file)
    st.text_area("Extracted Resume", resume_text, height=250)

    # Scoring
    st.subheader("📊 Scoring Results")
    results, fit_score = structured_score(resume_text, keyword_model)
    df = pd.DataFrame(results, columns=["Category", "Matched", "Total", "Matches", "Score", "Max Score"])
    st.dataframe(df)

    st.markdown(f"### ✅ Total Fit Score: **{fit_score}%**")
    if fit_score >= 80:
        st.success("✅ Strong Fit")
    elif fit_score >= 60:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    # Summary
    st.subheader("📝 Summary")
    for cat, matched, total, matches, _, _ in results:
        if matched > 0:
            st.markdown(f"- ✅ {cat}: {matched} / {total} → {', '.join(matches)}")
        else:
            st.markdown(f"- ❌ {cat}: No match")
