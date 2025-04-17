
import streamlit as st
st.set_page_config(page_title="Hybrid Resume Screener", layout="wide")

from docx import Document
import pandas as pd
from sentence_transformers import SentenceTransformer, util

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# --- Helper to extract text from docx ---
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

# --- Parse JD lines and assign weights ---
def parse_jd_blocks(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    blocks = []
    for line in lines:
        if line.lower().startswith("required:"):
            blocks.append(("Required", line[9:].strip(), 2.0))
        elif line.lower().startswith("preferred:"):
            blocks.append(("Preferred", line[10:].strip(), 1.5))
        elif line.lower().startswith("soft skills:"):
            blocks.append(("Soft Skills", line[12:].strip(), 1.0))
        else:
            blocks.append(("Other", line, 1.0))
    return blocks

# --- Hybrid semantic + keyword scorer ---
def hybrid_score(jd_blocks, resume_text):
    resume_lines = [l for l in resume_text.split("\n") if len(l.strip()) > 4]
    resume_embeddings = model.encode(resume_lines, convert_to_tensor=True)
    scored = []
    total = 0
    max_score = 0

    for label, jd_line, weight in jd_blocks:
        jd_embedding = model.encode(jd_line, convert_to_tensor=True)
        cosine_scores = util.cos_sim(jd_embedding, resume_embeddings)[0]
        max_cosine = float(cosine_scores.max())

        # Keyword fallback match
        fallback_hit = any(word.lower() in line.lower() for line in resume_lines for word in jd_line.split() if len(word) > 3)

        # Final score boost if keyword matched
        bonus = 0.1 if fallback_hit else 0
        match_score = max_cosine + bonus
        final_weighted = match_score * weight

        total += final_weighted
        max_score += weight

        scored.append((label, jd_line, round(max_cosine, 2), fallback_hit, weight, round(final_weighted, 2)))

    percent = round((total / max_score) * 100, 2) if max_score else 0
    return scored, percent

# --- UI layout ---
st.title("🔍 Hybrid Resume Screener (BERT + Keyword Enhanced)")

# JD Section
st.subheader("📌 Job Description (use Required:, Preferred:, Soft Skills:)")
jd_file = st.file_uploader("Upload JD (DOCX)", type=["docx"], key="jd_file")
jd_text = ""

if jd_file:
    jd_text = extract_text_from_docx(jd_file)

jd_text = st.text_area("✏️ Edit/Paste JD:", value=jd_text, height=200)
jd_blocks = parse_jd_blocks(jd_text)

# Resume Upload
st.subheader("📎 Resume Upload")
res_file = st.file_uploader("Upload Resume (DOCX)", type=["docx"], key="res_file")
if res_file:
    res_text = extract_text_from_docx(res_file)
    st.text_area("📄 Resume Content", res_text, height=250)

    # Score
    st.subheader("📊 Evaluation Results")
    results, final_percent = hybrid_score(jd_blocks, res_text)
    df = pd.DataFrame(results, columns=["Type", "JD Line", "BERT Match", "Keyword Hit", "Weight", "Score"])
    st.dataframe(df)

    st.markdown(f"### ✅ Total Fit Score: **{final_percent}%**")
    if final_percent >= 80:
        st.success("✅ Strong Fit")
    elif final_percent >= 60:
        st.warning("⚠️ Partial Fit")
    else:
        st.error("❌ Low Fit")

    st.subheader("🧠 Summary Insight")
    gaps = [r[1] for r in results if r[2] < 0.5 and not r[3]]
    hits = [r[1] for r in results if r[2] >= 0.65 or r[3]]
    if hits:
        st.markdown("**Matched Areas:**")
        for h in hits:
            st.markdown(f"- ✅ {h}")
    if gaps:
        st.markdown("**Gaps Found:**")
        for g in gaps:
            st.markdown(f"- ❌ {g}")
