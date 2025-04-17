
import streamlit as st
from docx import Document
import pandas as pd
from sentence_transformers import SentenceTransformer, util

# Load model
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# Extract text from DOCX
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

# Parse JD into categories with weights
def parse_jd(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    jd_sections = []
    for line in lines:
        if line.lower().startswith("required:"):
            jd_sections.append(("Required", line[9:].strip()))
        elif line.lower().startswith("preferred:"):
            jd_sections.append(("Preferred", line[10:].strip()))
        else:
            jd_sections.append(("Other", line.strip()))
    return jd_sections

# Semantic scoring
def semantic_score(jd_sections, resume_text):
    resume_lines = [l for l in resume_text.split("\n") if len(l.strip()) > 5]
    resume_embeddings = model.encode(resume_lines, convert_to_tensor=True)

    scored_sections = []
    total_score = 0
    max_score = 0

    for level, jd_item in jd_sections:
        jd_embedding = model.encode(jd_item, convert_to_tensor=True)
        cosine_scores = util.cos_sim(jd_embedding, resume_embeddings)[0]
        best_match_score = float(cosine_scores.max())
        weight = 2.0 if level == "Required" else 1.5 if level == "Preferred" else 1.0
        score = best_match_score * weight
        total_score += score
        max_score += weight
        scored_sections.append((level, jd_item, round(best_match_score, 2), weight, round(score, 2)))

    percentage = round((total_score / max_score) * 100, 2) if max_score else 0
    return scored_sections, percentage

# Streamlit UI
st.set_page_config(page_title="Semantic Resume Screener", layout="wide")
st.title("🧠 Threat Engineer Resume Screener – Semantic Enhanced")

# JD Input
st.subheader("📌 Job Description Input")
jd_file = st.file_uploader("Upload JD (DOCX)", type=["docx"], key="jd_file")
jd_text = ""

if jd_file:
    jd_text = extract_text_from_docx(jd_file)

jd_text = st.text_area("Edit or Paste JD (Use 'Required:', 'Preferred:' prefixes)", jd_text, height=200)
jd_sections = parse_jd(jd_text)

# Resume Upload
st.subheader("📎 Upload Resume (DOCX)")
resume_file = st.file_uploader("Upload Resume", type=["docx"], key="resume_file")
if resume_file:
    resume_text = extract_text_from_docx(resume_file)
    st.text_area("Extracted Resume Text", resume_text, height=250)

    # Score
    st.subheader("📊 Semantic Scoring Summary")
    results, score_percent = semantic_score(jd_sections, resume_text)
    df = pd.DataFrame(results, columns=["JD Level", "JD Requirement", "Best Match", "Weight", "Weighted Score"])
    st.dataframe(df)

    st.markdown(f"### ✅ Total Fit Score: **{score_percent}%**")

    if score_percent >= 80:
        st.success("✅ Strong Fit")
    elif score_percent >= 60:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    st.subheader("📝 Smart Feedback")
    gaps = [r[1] for r in results if r[2] < 0.5]
    strengths = [r[1] for r in results if r[2] >= 0.7]

    if strengths:
        st.markdown(f"**Strength Areas:** {', '.join(strengths)}")
    if gaps:
        st.markdown(f"**Gaps Identified:** {', '.join(gaps)}")
    else:
        st.markdown("No major gaps found. Resume strongly aligns with JD.")
