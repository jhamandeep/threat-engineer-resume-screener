import streamlit as st
from docx import Document

# --- Static base criteria (can be mapped from JD later) ---
default_criteria = {
    "Threat Platforms (SkyHigh, Trellix, McAfee)": ["SkyHigh", "Trellix", "McAfee Web Gateway"],
    "Deployment & Infra Design": ["deployment", "implementation", "infrastructure", "refresh", "lifecycle"],
    "SIEM / Detection": ["SIEM", "Sentinel", "QRadar", "Splunk", "EDR"],
    "Network / Proxy / DMZ": ["DMZ", "proxy", "routing", "Cisco", "TLS", "SSL"],
    "Scripting / Programming": ["Python", "PowerShell", "Bash", "Shell", "KQL"],
    "Certifications": ["CISSP", "CCNA", "NSE", "Microsoft Certified", "CEH"],
    "Audit & Compliance": ["ISO", "SOC2", "compliance", "NIST", "audit"],
    "Sector Fit": ["bank", "financial", "government", "telecom", "energy"],
    "Soft Skills": ["documentation", "training", "communication", "stakeholder", "presentation", "leadership"]
}

# --- Functions ---
def extract_text_from_docx(uploaded_file):
    try:
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[Error extracting text: {e}]"

def evaluate_resume(text, criteria):
    scorecard = []
    total = 0
    max_score = len(criteria) * 5
    missing = []
    exceeding = []
    
    for category, keywords in criteria.items():
        match_count = sum(1 for k in keywords if k.lower() in text.lower())
        if match_count >= len(keywords) * 0.8:
            rating = 5
            comment = "Significantly exceeds expectations"
            exceeding.append(category)
        elif match_count >= len(keywords) * 0.5:
            rating = 4
            comment = "Exceeds expectations"
        elif match_count >= 1:
            rating = 3
            comment = "Meets expectations"
        else:
            rating = 1
            comment = "Missing from resume"
            missing.append((category, keywords))
        
        total += rating
        scorecard.append((category, rating, comment))
    return scorecard, total, max_score, missing, exceeding

def generate_feedback(scorecard, missing, exceeding):
    level = "Strong" if len(exceeding) >= 4 else "Partial" if len(exceeding) >= 2 else "Limited"
    feedback = f"Candidate shows **{level} alignment** to the JD.\n\n"
    if exceeding:
        feedback += f"**Exceeds expectations** in: {', '.join(exceeding)}.\n"
    if missing:
        feedback += f"**Missing key areas**: {', '.join([m[0] for m in missing])}.\n"
    return feedback

# --- UI ---
st.set_page_config(page_title="Threat Engineer Screener", layout="wide")
st.title("🛡️ Threat Engineer Resume Screener")

# JD input section
st.subheader("📌 Job Description Input")
jd_input = st.text_area("Paste JD or customize below:", "\n".join(default_criteria.keys()), height=200)

# Parse JD to criteria format
jd_lines = [line.strip() for line in jd_input.strip().split("\n") if line.strip()]
jd_criteria = {line: default_criteria.get(line, []) for line in jd_lines}

# Resume upload
st.subheader("📎 Upload Resume (DOCX only)")
uploaded_file = st.file_uploader("Upload candidate resume", type=["docx"])

if uploaded_file:
    resume_text = extract_text_from_docx(uploaded_file)

    st.subheader("📄 Resume Text Preview")
    st.text_area("Extracted Resume Text", resume_text, height=300)

    # Evaluate
    st.subheader("📊 Evaluation Summary")
    scorecard, total, max_score, missing, exceeding = evaluate_resume(resume_text, jd_criteria)
    percent = round((total / max_score) * 100, 2)

    st.markdown(f"**Total Score:** {total} / {max_score} → **{percent}%**")

    if percent >= 75:
        st.success("✅ Strong Fit")
    elif percent >= 50:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    # Show table
    st.subheader("📋 Detailed Scorecard")
    st.table(pd.DataFrame(scorecard, columns=["Category", "Rating (1–5)", "Comments"]))

    # Gap analysis
    st.subheader("🧭 Gap & Excellence Analysis")
    if missing:
        st.markdown("**🔻 Missing or Weak Areas:**")
        for cat, keywords in missing:
            st.markdown(f"- ❌ {cat} (Expected keywords: *{', '.join(keywords)}*)")
    if exceeding:
        st.markdown("**🌟 Exceeded in:**")
        for cat in exceeding:
            st.markdown(f"- ⭐ {cat}")

    # Feedback block
    st.subheader("📝 Feedback Summary")
    feedback = generate_feedback(scorecard, missing, exceeding)
    st.markdown(feedback)
