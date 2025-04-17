# Threat Engineer Resume Screening App (v2 - Fixed)
import streamlit as st
from docx import Document

# --- Screening Criteria and Weights ---
criteria = {
    "Years of Security Experience": (10, ["5+", "6+", "7+", "8+", "more than 5", "over 5"]),
    "SkyHigh / Trellix / McAfee": (15, ["SkyHigh", "Trellix", "McAfee Web Gateway"]),
    "Threat Engineering Deployment (Infra + Lifecycle)": (15, ["deployment", "implementation", "lifecycle", "refresh", "infrastructure"]),
    "SIEM / Threat Detection Tools": (10, ["SIEM", "QRadar", "Sentinel", "Splunk", "EDR"]),
    "DMZ / Proxy / Routing Knowledge": (10, ["DMZ", "proxy", "routing", "SSL/TLS", "Cisco"]),
    "Programming / Scripting": (8, ["Python", "PowerShell", "KQL", "Bash", "Shell"]),
    "Certifications": (7, ["CISSP", "CCNA", "CEH", "NSE", "Microsoft Certified"]),
    "Audit / Compliance Experience": (8, ["ISO", "SOC2", "audit", "compliance", "NIST"]),
    "Sector Experience (Banking, Govt, Telecom)": (5, ["bank", "financial", "government", "telecom", "energy"]),
    "Communication & Documentation": (6, ["documentation", "reports", "training", "stakeholder", "collaboration"]),
    "Architecture / Design Thinking": (6, ["architecture", "design", "SME", "strategy", "planning"])
}

# --- Extract text from DOCX ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return "Error extracting text: " + str(e)

# --- Scoring Function ---
def score_resume(text):
    total_score = 0
    max_score = sum(weight for weight, _ in criteria.values())
    detailed_scores = {}

    for category, (weight, keywords) in criteria.items():
        found = any(keyword.lower() in text.lower() for keyword in keywords)
        score = weight if found else 0
        detailed_scores[category] = (score, weight, "✔️" if found else "❌")
        total_score += score

    return total_score, max_score, detailed_scores

# --- Streamlit App UI ---
def main():
    st.set_page_config(page_title="Threat Engineer Resume Screener", layout="centered")
    st.title("🛡️ Threat Engineer Resume Screener")

    uploaded_file = st.file_uploader("Upload Resume (DOCX only)", type=["docx"])
    if uploaded_file:
        resume_text = extract_text_from_docx(uploaded_file)

        st.subheader("📄 Extracted Resume Text")
        st.text_area("Resume Content", resume_text, height=250)

        st.subheader("📊 Scoring Results")
        total, max_score, results = score_resume(resume_text)
        percent = round((total / max_score) * 100, 2)

        st.write(f"**Total Score:** {total} / {max_score} (**{percent}%**)")

        if percent >= 75:
            st.success("✅ Strong Fit for the Role")
        elif percent >= 50:
            st.warning("⚠️ Partial Fit – Consider with Caution")
        else:
            st.error("❌ Low Fit – Not Recommended")

        st.subheader("🔍 Breakdown by Category")
        for category, (score, weight, status) in results.items():
            st.markdown(f"- **{category}** [{status}] → {score} / {weight}")

if __name__ == "__main__":
    main()

