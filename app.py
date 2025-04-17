
import streamlit as st
from docx import Document
import pandas as pd

st.set_page_config(page_title="Resume JD Fit Analyzer", layout="wide")

# Extract text from .docx
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# Convert JD text to keyword buckets
def parse_jd_into_sections(text):
    jd_sections = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    current_section = None
    for line in lines:
        if ":" in line:
            section, value = line.split(":", 1)
            jd_sections[section.strip()] = [kw.strip() for kw in value.split(",") if kw.strip()]
    return jd_sections

# Match resume against JD buckets
def match_resume(resume_text, jd_sections):
    results = []
    total_score = 0
    verdict_map = {"✔": 5, "⚠": 3, "✘": 0}
    for section, keywords in jd_sections.items():
        match_count = sum(1 for kw in keywords if kw.lower() in resume_text.lower())
        if match_count == len(keywords):
            verdict = "✔"
        elif match_count >= 1:
            verdict = "⚠"
        else:
            verdict = "✘"
        score = verdict_map[verdict]
        results.append((section, ", ".join(keywords), match_count, verdict, score))
        total_score += score
    max_score = len(jd_sections) * 5
    fit_percent = round((total_score / max_score) * 100, 2)
    fit_label = "✅ Strong Fit" if fit_percent >= 80 else "⚠️ Partial Fit" if fit_percent >= 60 else "❌ Low Fit"
    return results, fit_percent, fit_label

# UI
st.title("📄 Resume vs JD Analyzer")

st.subheader("📌 Upload JD (DOCX with format like 'Category: keyword1, keyword2')")
jd_file = st.file_uploader("Upload JD File", type=["docx"], key="jd_file")
jd_text = ""
if jd_file:
    jd_text = extract_text_from_docx(jd_file)
    jd_sections = parse_jd_into_sections(jd_text)
    st.success("JD parsed successfully.")
    st.dataframe(pd.DataFrame.from_dict(jd_sections, orient='index').transpose())

st.subheader("📎 Upload Resume (DOCX)")
resume_file = st.file_uploader("Upload Resume File", type=["docx"], key="resume_file")

if resume_file and jd_text:
    resume_text = extract_text_from_docx(resume_file)
    st.subheader("📊 Evaluation Result")
    results, fit_percent, fit_label = match_resume(resume_text, jd_sections)
    df = pd.DataFrame(results, columns=["Category", "JD Keywords", "Matches Found", "Verdict", "Score"])
    st.dataframe(df)
    st.markdown(f"### Final JD Fit Score: **{fit_percent}%** → {fit_label}")
else:
    st.info("Please upload both JD and Resume to proceed.")
