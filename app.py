
import streamlit as st
from docx import Document
import pandas as pd

# --- Base keyword mappings ---
default_keywords = {
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

# --- Helpers ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"[Error extracting text: {e}]"

def extract_jd_criteria(text_block):
    lines = [line.strip("•*-•:\n ") for line in text_block.split("\n") if len(line.strip()) > 4]
    jd_criteria = {}
    for line in lines:
        matches = [k for k, v in default_keywords.items() if any(kw.lower() in line.lower() for kw in v)]
        if matches:
            jd_criteria[matches[0]] = default_keywords[matches[0]]
        else:
            # fallback to tokenizing line itself
            jd_criteria[line[:40]] = [word.strip(",.():") for word in line.split() if len(word) > 3]
    return jd_criteria

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

# --- Streamlit App ---
st.set_page_config(page_title="Threat Engineer Screener", layout="wide")
st.title("🛡️ Threat Engineer Resume Screener")

# 📎 JD Upload + Editor
st.subheader("📌 Upload or Edit Job Description")
jd_file = st.file_uploader("Upload JD (DOCX)", type=["docx"], key="jd_upload")
jd_text = ""

if jd_file:
    jd_text = extract_text_from_docx(jd_file)
    st.success("✅ JD file uploaded and parsed.")

jd_text = st.text_area("📝 Edit JD or paste here:", value=jd_text or "\n".join(default_keywords.keys()), height=250)
jd_criteria = extract_jd_criteria(jd_text)

# 📄 Resume Upload
st.subheader("📎 Upload Resume (DOCX only)")
resume_file = st.file_uploader("Upload candidate resume", type=["docx"], key="resume_upload")

if resume_file:
    resume_text = extract_text_from_docx(resume_file)
    st.subheader("📄 Resume Text Preview")
    st.text_area("Resume Content", resume_text, height=300)

    # 🧠 Evaluate
    st.subheader("📊 Evaluation Summary")
    scorecard, total, max_score, missing, exceeding = evaluate_resume(resume_text, jd_criteria)
    percent = round((total / max_score) * 100, 2)

    st.markdown(f"**Total Score:** `{total}` / `{max_score}` → **{percent}%**")

    if percent >= 75:
        st.success("✅ Strong Fit")
    elif percent >= 50:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    st.subheader("📋 Detailed Scorecard")
    st.table(pd.DataFrame(scorecard, columns=["Category", "Rating (1–5)", "Comments"]))

    st.subheader("🧭 Gap & Excellence Analysis")
    if missing:
        st.markdown("**🔻 Missing Areas:**")
        for cat, keywords in missing:
            st.markdown(f"- ❌ {cat} — *Expected:* `{', '.join(keywords)}`")
    if exceeding:
        st.markdown("**🌟 Exceeds Expectations In:**")
        for cat in exceeding:
            st.markdown(f"- ⭐ {cat}")

    st.subheader("📝 Feedback Summary")
    feedback = generate_feedback(scorecard, missing, exceeding)
    st.markdown(feedback)
