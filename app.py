import streamlit as st
import spacy
import io
import re
from docx import Document
import PyPDF2

# --- SpaCy Model Loading ---
# Define the spaCy model name
MODEL_NAME = "en_core_web_sm"

@st.cache_resource # Use st.cache_resource for caching models/connections
def load_spacy_model(model_name: str):
    """
    Loads the spaCy model, assuming it has been installed via requirements.txt.
    Uses st.cache_resource to cache the model in memory.
    """
    try:
        nlp = spacy.load(model_name)
        st.success(f"Successfully loaded spaCy model: {model_name}")
        return nlp
    except OSError:
        st.error(f"SpaCy model '{model_name}' not found.")
        st.info("Please ensure 'en_core_web_sm' or its wheel file URL is in your requirements.txt and check the deployment logs.")
        st.stop() # Stop the app execution if model cannot be loaded
    except Exception as e:
         st.error(f"An unexpected error occurred during model loading: {e}")
         st.stop()

# Load the spaCy model using the cached function
nlp = load_spacy_model(MODEL_NAME)

# --- Text Extraction Functions ---

def extract_text_from_pdf(file_obj):
    """Extracts text from a PDF file object."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        if len(reader.pages) > 0:
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                     # Optional: Handle pages that might not have extractable text
                     pass # Or add a placeholder: text += "[Non-extractable page]\n"
        return text if text else None # Return None if no text was extracted
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(file_obj):
    """Extracts text from a DOCX file object."""
    text = ""
    try:
        document = Document(file_obj)
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
        return text if text else None # Return None if no text was extracted
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {e}")
        return None

def clean_text(text):
    """Basic text cleaning: lowercase, remove extra whitespace and some special characters."""
    if not text:
        return ""
    text = text.lower()
    # Replace common special characters with spaces or remove them
    text = re.sub(r'[^a-z0-9\s.-]', '', text) # Keep letters, numbers, spaces, periods, hyphens
    text = re.sub(r'\s+', ' ', text).strip() # Replace multiple spaces with a single space
    return text

# --- Keyword/Requirement Extraction from JD (Needs Customization) ---

def extract_keywords_from_jd(jd_text):
    """
    Extracts potential keywords/requirements from JD text.
    This is a simplified example. You will need to customize this
    based on typical Threat Engineer JDs.

    Ideas for improvement:
    - Use spaCy's PhraseMatcher or EntityRuler for specific skills/technologies.
    - Look for patterns like "X+ years of experience in Y".
    - Identify sections like "Required Qualifications", "Responsibilities".
    """
    if not jd_text:
        return []

    doc = nlp(jd_text)

    # --- Simple Keyword Extraction Example ---
    # Collect important noun chunks and proper nouns as potential keywords
    keywords = set()
    for chunk in doc.noun_chunks:
        # Filter short or common noun chunks
        chunk_text = clean_text(chunk.text)
        if len(chunk_text) > 2 and chunk_text not in nlp.Defaults.stop_words:
             keywords.add(chunk_text)

    for ent in doc.ents:
        # Add specific entity types that might be relevant (ORG, GPE, PRODUCT, etc.)
        if ent.label_ in ["ORG", "PRODUCT", "NORP", "GPE"]: # Example entity types
             ent_text = clean_text(ent.text)
             if len(ent_text) > 2 and ent_text not in nlp.Defaults.stop_words:
                keywords.add(ent_text)


    # --- Add domain-specific keywords manually ---
    # This is highly recommended for better accuracy
    threat_eng_keywords = [
        "penetration testing", "vulnerability assessment", "SIEM", "firewall",
        "IDS", "IPS", "malware analysis", "incident response", "security operations center",
        "SOC", "threat hunting", "forensics", "network security", "endpoint security",
        "cloud security", "AWS security", "Azure security", "GCP security", "OWASP",
        "security frameworks", "CIS Controls", "NIST", "ISO 27001", "risk assessment",
        "python", "bash", "scripting", "security tools", "wireshark", "nmap",
        "metasploit", "burp suite", "security architecture", "cryptography",
        "identity and access management", "IAM", "DevSecOps", "threat modeling"
        # Add more keywords relevant to Threat Engineering
    ]
    for kw in threat_eng_keywords:
        keywords.add(clean_text(kw))


    # Convert set to list and sort for consistent output
    return sorted(list(keywords))


# --- Resume Analysis and Scoring ---

def analyze_resume(resume_text, jd_keywords):
    """
    Analyzes resume text against a list of JD keywords.
    Returns strengths, gaps, and a match percentage.
    """
    if not resume_text or not jd_keywords:
        return [], jd_keywords, 0.0

    cleaned_resume_text = clean_text(resume_text)
    strengths = []
    gaps = []
    matched_count = 0

    # Simple check for presence of keywords in the cleaned resume text
    for keyword in jd_keywords:
        # Use regex for more robust matching (e.g., whole words)
        pattern = r'\b' + re.escape(keyword) + r'\b' # Matches whole word
        if re.search(pattern, cleaned_resume_text):
            strengths.append(keyword)
            matched_count += 1
        else:
            gaps.append(keyword)

    total_keywords = len(jd_keywords)
    score = (matched_count / total_keywords) * 100 if total_keywords > 0 else 0

    return sorted(strengths), sorted(gaps), score

# --- Streamlit App Interface ---

st.title("AI-Powered Resume Screener for Threat Engineers")

st.write("Upload a Job Description and a Candidate Resume (PDF or DOCX) for analysis.")

# File Uploaders
jd_file = st.file_uploader("Upload Job Description (PDF or DOCX)", type=["pdf", "docx"], key="jd_uploader")
resume_file = st.file_uploader("Upload Candidate Resume (PDF or DOCX)", type=["pdf", "docx"], key="resume_uploader")

# Threshold for screening
screening_threshold = st.slider("Set Screening Score Threshold (%)", 0, 100, 60) # Default threshold at 60%

analyze_button = st.button("Analyze Resume")

if analyze_button:
    if jd_file is None or resume_file is None:
        st.warning("Please upload both the Job Description and the Candidate Resume.")
    else:
        with st.spinner("Extracting text and analyzing..."):
            # Extract text from JD
            jd_extension = jd_file.name.split(".")[-1].lower()
            jd_text = None
            jd_bytes = io.BytesIO(jd_file.getvalue())
            if jd_extension == "pdf":
                jd_text = extract_text_from_pdf(jd_bytes)
            elif jd_extension == "docx":
                jd_text = extract_text_from_docx(jd_bytes)

            # Extract text from Resume
            resume_extension = resume_file.name.split(".")[-1].lower()
            resume_text = None
            resume_bytes = io.BytesIO(resume_file.getvalue())
            if resume_extension == "pdf":
                resume_text = extract_text_from_pdf(resume_bytes)
            elif resume_extension == "docx":
                resume_text = extract_text_from_docx(resume_bytes)

            if not jd_text:
                st.error("Could not extract text from the Job Description file.")
            elif not resume_text:
                st.error("Could not extract text from the Candidate Resume file.")
            else:
                # Process JD to get keywords/requirements
                jd_keywords = extract_keywords_from_jd(jd_text)

                if not jd_keywords:
                     st.warning("Could not extract relevant keywords from the Job Description. Analysis may be inaccurate.")
                     st.info("Consider manually adding keywords within the `extract_keywords_from_jd` function in the code.")

                # Analyze Resume against JD keywords
                strengths, gaps, score = analyze_resume(resume_text, jd_keywords)

                # --- Display Results ---
                st.subheader("Analysis Results")

                # Screening Score
                st.write(f"**Screening Score:** {score:.2f}%")

                # Screening Decision
                if score >= screening_threshold:
                    st.success(f"✅ Candidate Screened In (Score >= {screening_threshold}%)")
                else:
                    st.warning(f"❌ Candidate Not Screened In (Score < {screening_threshold}%)")

                # Strengths and Gaps
                st.subheader("Resume vs. Job Description")

                if strengths:
                    st.info("🚀 Strengths (Matched Keywords/Requirements):")
                    for strength in strengths:
                        st.write(f"- {strength}")
                else:
                     st.info("🤔 No specific keywords/requirements from the JD were clearly found in the resume.")

                if gaps:
                    st.warning("❗️ Gaps (Keywords/Requirements Not Found):")
                    for gap in gaps:
                        st.write(f"- {gap}")
                else:
                    st.success("🎉 All identified keywords/requirements from the JD were found!")


                # Transparent Feedback/Reasoning
                st.subheader("Transparent Feedback")
                if score >= screening_threshold:
                    st.write("The candidate's resume shows a good match with the key requirements identified in the Job Description. Key strengths include:")
                    if strengths:
                         for strength in strengths:
                              st.markdown(f"- {strength}")
                    else:
                         st.write("Based on the analysis, the resume aligns well with the JD.")
                else:
                    st.write(f"The candidate was not screened in because the match score ({score:.2f}%) is below the required threshold ({screening_threshold}%).")
                    if gaps:
                        st.write("Key areas where the resume did not match the Job Description's identified requirements include:")
                        for gap in gaps:
                            st.markdown(f"- {gap}")
                    else:
                        st.write("Analysis did not find sufficient overlap with the Job Description's keywords.")

                st.markdown("---")
                st.markdown("_**Note:** This analysis is based on keyword matching. A thorough manual review is always recommended for the final decision._")


                # Optional: Show extracted text (useful for debugging)
                with st.expander("Show Extracted Text"):
                    if jd_text:
                        st.subheader("Job Description Text:")
                        st.text(jd_text[:2000] + ("..." if len(jd_text) > 2000 else ""))
                    if resume_text:
                        st.subheader("Resume Text:")
                        st.text(resume_text[:2000] + ("..." if len(resume_text) > 2000 else ""))
