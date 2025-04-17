
import streamlit as st
st.set_page_config(page_title="Threat Engineer Resume Screener", layout="wide")

from docx import Document
import pandas as pd

# --- Fixed Criteria and Keywords ---
criteria = {
    "Threat Platforms (SkyHigh, Trellix, McAfee)": ["SkyHigh", "Trellix", "McAfee Web Gateway"],
    "Deployment & Infra Design": ["deployment", "implementation", "infrastructure", "refresh", "lifecycle"],
    "SIEM / Detection": ["SIEM", "Sentinel", "QRadar", "Splunk", "EDR"],
    "Network / Proxy / DMZ": ["DMZ", "proxy", "routing", "Cisco", "TLS", "SSL"],
    "Scripting / Programming": ["Python", "PowerShell", "Bash", "Shell", "KQL"],
    "Certifications": ["CISSP", "CCNA", "NSE", "Microsoft Certified", "CEH"],
    "Audit & Compliance": ["ISO", "SOC2", "compliance", "NIST", "audit"],
    "Sector Fit": ["bank", "financial", "government", "telecom", "energy"],
    "Soft Skills": ["documentation", "training", "communication", "stakeholder", "presentation", "leadership"],
    "Experience Level": ["5+", "6+", "7+", "8+", "more than 5", "over 5"],
    "Architecture / Design Thinking": ["architecture", "design", "SME", "strategy", "planning"]
}

# Extract text from DOCX
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

# Score function
def score_resume(text):
    scorecard = []
    total_score = 0
    max_score = len(criteria) * 5
    missing = []
    matched = []

    for category, keywords in criteria.items():
        match_count = sum(1 for k in keywords if k.lower() in text.lower())
        if match_count >= len(keywords) * 0.8:
            rating = 5
            comment = "✔️ Significantly exceeds expectations"
            matched.append((category, comment))
        elif match_count >= len(keywords) * 0.5:
            rating = 4
            comment = "✔️ Exceeds expectations"
            matched.append((category, comment))
        elif match_count >= 1:
            rating = 3
            comment = "⚠️ Meets some expectations"
            matched.append((category, comment))
        else:
            rating = 1
            comment = "❌ Missing"
            missing.append((category, keywords))
        total_score += rating
        scorecard.append((category, rating, comment))

    percent = round((total_score / max_score) * 100, 2)
    return scorecard, total_score, max_score, percent, matched, missing

# Streamlit App
st.title("✅ Original Rule-Based Threat Engineer Resume Screener")

# Resume Upload
st.subheader("📎 Upload Resume (DOCX only)")
res_file = st.file_uploader("Upload Resume", type=["docx"])
if res_file:
    text = extract_text_from_docx(res_file)
    st.subheader("📄 Resume Preview")
    st.text_area("Extracted Resume Text", text, height=300)

    st.subheader("📊 Evaluation")
    scorecard, total, max_score, percent, matched, missing = score_resume(text)
    st.markdown(f"**Total Score:** {total} / {max_score} → **{percent}%**")

    if percent >= 75:
        st.success("✅ Strong Fit")
    elif percent >= 50:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    st.subheader("📋 Detailed Scorecard")
    df = pd.DataFrame(scorecard, columns=["Category", "Score", "Remarks"])
    st.dataframe(df)

    st.subheader("✅ Matched Areas")
    for cat, comment in matched:
        st.markdown(f"- {comment} → **{cat}**")

    st.subheader("❌ Gaps Identified")
    for cat, keywords in missing:
        st.markdown(f"- {cat} — _Expected:_ `{', '.join(keywords)}`")
