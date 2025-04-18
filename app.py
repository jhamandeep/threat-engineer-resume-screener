import streamlit as st
import spacy
import re
import io
from collections import Counter

# --- Text Extraction Libraries ---
# Using PyPDF2 (make sure it's uncommented in requirements.txt)
try:
    import PyPDF2
    PDF_READER_LIB = "pypdf2"
except ImportError:
    st.error("PyPDF2 not installed. Please add 'pypdf2' to your requirements.txt")
    st.stop()

# Using PyMuPDF (make sure it's uncommented in requirements.txt and pypdf2 is commented out)
# try:
#     import fitz # pymupdf
#     PDF_READER_LIB = "pymupdf"
# except ImportError:
#     st.error("PyMuPDF not installed. Please add 'pymupdf' to your requirements.txt")
#     st.stop()


# DOCX Library
try:
    from docx import Document
except ImportError:
    st.error("Please install 'python-docx' (`pip install python-docx`) to process .docx files.")
    # Create a dummy Document class if python-docx is not installed
    class Document:
        def __init__(self):
            self.paragraphs = []


# --- Load NLP Model ---
SPACY_MODEL_NAME = "en_core_web_sm"

# Load the spaCy model once at the start
@st.cache_resource # Use cache_resource for models/connections
def load_spacy_model(model_name=SPACY_MODEL_NAME):
    """Loads the spaCy model and handles potential errors."""
    try:
        return spacy.load(model_name)
    except OSError:
        # Don't use st.error here as it halts the app. Log or print instead.
        print(f"spaCy model '{model_name}' not found. Attempting download (may not work on all platforms)...")
        try:
            spacy.cli.download(model_name)
            return spacy.load(model_name)
        except Exception as e:
            st.error(f"Failed to load or download spaCy model '{model_name}'. Please ensure it's installed or downloadable in the deployment environment. Error: {e}")
            st.stop() # Stop execution if model isn't available after download attempt

nlp = load_spacy_model()


# --- Text Extraction Functions ---

def extract_text_from_pdf_pypdf2(file_bytes):
    """Extracts text from PDF bytes using PyPDF2."""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text: # Check if text extraction was successful for the page
                text += page_text + "\n" # Add newline for better separation
        return text
    except Exception as e:
        st.error(f"Error reading PDF (PyPDF2): {e}")
        return ""

def extract_text_from_pdf_pymupdf(file_bytes):
    """Extracts text from PDF bytes using PyMuPDF."""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF (PyMuPDF): {e}")
        return ""

def extract_text_from_docx(file_bytes):
    """Extracts text from DOCX bytes."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        # Handle cases where the file might not be a valid DOCX
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text(uploaded_file):
    """Extracts text from uploaded file based on its type."""
    if uploaded_file is None:
        return ""

    # Read file content as bytes
    try:
        file_bytes = uploaded_file.getvalue()
    except Exception as e:
        st.error(f"Error reading uploaded file: {e}")
        return ""

    # Get file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()

    text = ""
    if file_extension == "pdf":
        if PDF_READER_LIB == "pypdf2":
             text = extract_text_from_pdf_pypdf2(file_bytes)
        elif PDF_READER_LIB == "pymupdf":
             text = extract_text_from_pdf_pymupdf(file_bytes)
        else:
             st.error("No valid PDF reader library configured.")
             return ""
    elif file_extension == "docx":
        text = extract_text_from_docx(file_bytes)
    elif file_extension == "txt":
        # Decode bytes with error handling
        try:
            text = file_bytes.decode("utf-8", errors='ignore')
        except Exception as e:
             st.error(f"Error reading TXT: {e}")
             return ""
    else:
        st.warning(f"Unsupported file type: {file_extension}. Please upload PDF, DOCX, or TXT.")
        return "" # Return empty string for unsupported types

    # Basic cleaning: Remove excessive whitespace
    if text:
        text = re.sub(r'\s+', ' ', text).strip()
    return text


# --- NLP and Matching Functions ---

def extract_keywords_and_entities(text):
    """Extracts potential skills, tools, and named entities using spaCy."""
    if not text or not nlp: # Check if NLP model loaded
        return set() # Return empty set if no text or model failed

    doc = nlp(text.lower()) # Process text in lowercase

    # Extract potential skills/keywords (nouns, proper nouns, adjectives)
    # Use noun chunks for better multi-word skills
    keywords = set()
    for chunk in doc.noun_chunks:
         # Simple filter: length > 1, contains alpha characters
        if len(chunk.text.split()) > 0 and any(c.isalpha() for c in chunk.text):
             keywords.add(chunk.lemma_.strip()) # Use lemma of the chunk

    # Add single nouns/proper nouns not part of chunks
    for token in doc:
        if token.pos_ in ["NOUN", "PROPN"] and token.is_alpha and not token.is_stop and not token.text.lower() in keywords:
            keywords.add(token.lemma_)

    # Extract named entities
    entities = set()
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT", "TECH", "LANGUAGE", "NORP", "GPE", "WORK_OF_ART"]: # Add more relevant types if needed
             entities.add(ent.text.lower().strip())

    combined = keywords.union(entities)
    # Optional: Filter out very short terms
    combined = {term for term in combined if len(term) > 2}
    return combined


def calculate_score(resume_keywords, jd_keywords):
    """Calculates a match score based on keyword overlap."""
    if not jd_keywords: # Avoid division by zero if JD has no keywords
        return 0.0, set()

    # Find common keywords
    common_keywords = resume_keywords.intersection(jd_keywords)

    # Score: Ratio of common keywords to total JD keywords
    score = (len(common_keywords) / len(jd_keywords)) * 100 if jd_keywords else 0.0

    return score, common_keywords


def analyze_strengths_gaps(resume_keywords, jd_keywords):
    """Identifies strengths (matching keywords) and gaps (missing keywords)."""
    strengths = resume_keywords.intersection(jd_keywords)
    gaps = jd_keywords.difference(resume_keywords)
    return strengths, gaps

def generate_rating(score):
    """Assigns a rating based on the calculated score."""
    if score >= 90:
        return 5 # Significantly exceeded expectations
    elif score >= 75:
        return 4 # Exceeded expectations
    elif score >= 60:
        return 3 # Met expectations
    elif score >= 40:
        return 2 # Met expectations with reservations
    else:
        return 1 # Did not meet expectations


# --- Streamlit App UI ---

st.set_page_config(layout="wide", page_title="Resume Screener")
st.title("📄 Resume Screening Assistant")
st.markdown("Upload a Job Description (JD) and Resumes to find the best fit based on keyword matching.")

# --- Sidebar for Uploads and JD ---
with st.sidebar:
    st.header("⚙️ Configuration")

    # --- Job Description ---
    jd_file = st.file_uploader("1. Upload Job Description", type=["pdf", "docx", "txt"], key="jd")
    jd_text_extracted = extract_text(jd_file) if jd_file else ""

    st.subheader("Job Description Content")
    # Allow editing of the extracted JD text
    jd_text_final = st.text_area("Edit or paste JD text here:", value=jd_text_extracted, height=300, key="jd_edit", placeholder="Paste the Job Description here...")

    # --- Resume Upload ---
    resume_files = st.file_uploader("2. Upload Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True, key="resumes")

    # --- Process Button ---
    st.markdown("---")
    process_button = st.button("🚀 Analyze Resumes", key="process", use_container_width=True, type="primary")


# --- Main Area for Results ---
st.header("📊 Analysis Results")

if process_button and jd_text_final and resume_files:
    if not nlp:
         st.error("NLP Model not loaded. Cannot process.")
         st.stop()

    # Extract keywords from the final JD
    with st.spinner("Analyzing Job Description..."):
        jd_keywords = extract_keywords_and_entities(jd_text_final)

    if not jd_keywords:
        st.warning("Could not extract significant keywords from the Job Description. Please ensure it has enough detail or check the text extraction.")
        st.stop()

    st.info(f"Found {len(jd_keywords)} unique keywords/entities in the Job Description.")
    with st.expander("View JD Keywords/Entities"):
        st.write(sorted(list(jd_keywords)))

    st.markdown("---") # Separator

    results = []
    # Process each resume
    overall_progress = st.progress(0)
    status_text = st.empty()

    for i, resume_file in enumerate(resume_files):
        status_text.text(f"Processing file {i+1}/{len(resume_files)}: {resume_file.name}")
        # Update progress bar
        overall_progress.progress((i + 1) / len(resume_files))

        resume_text = extract_text(resume_file)

        if not resume_text:
            st.error(f"Could not extract text from {resume_file.name}. Skipping.")
            results.append({ # Add a placeholder for skipped files
                "filename": resume_file.name, "score": 0, "rating": 0,
                "error": "Text extraction failed", "candidate_name": resume_file.name.split('.')[0]
            })
            continue # Skip to the next file

        # Extract keywords from the resume
        resume_keywords = extract_keywords_and_entities(resume_text)

        # Calculate score and matching keywords
        score, common_keywords = calculate_score(resume_keywords, jd_keywords)

        # Analyze strengths and gaps
        strengths, gaps = analyze_strengths_gaps(resume_keywords, jd_keywords)

        # Generate rating
        rating = generate_rating(score)

        # Store results
        results.append({
            "filename": resume_file.name,
            "score": score,
            "rating": rating,
            "strengths": strengths,
            "gaps": gaps,
            "common_keywords": common_keywords,
             # Placeholder values - need more advanced extraction
            "candidate_name": resume_file.name.split('.')[0], # Basic name guess
            "error": None
            # Fields from image (require more advanced parsing not implemented here)
            # "position_applied": "N/A",
            # "location": "N/A",
            # "overall_experience": "N/A",
            # "relevant_experience": "N/A"
        })

    status_text.text(f"Processing complete! Analyzed {len(resume_files)} resumes.")
    overall_progress.empty() # Remove progress bar after completion


    # Sort results by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)

    # Display results
    for i, result in enumerate(results):
        st.markdown(f"### {i+1}. Candidate: {result['candidate_name']} (File: {result['filename']})")

        if result.get("error"):
            st.error(f"Could not process this file: {result['error']}")
            st.markdown("---")
            continue

        col1, col2 = st.columns([1, 3]) # Ratio for columns

        with col1:
            st.metric(label="Match Score", value=f"{result['score']:.1f}%")
            st.metric(label="Rating", value=f"{result['rating']} / 5")
            st.progress(int(result['score']) / 100)

        with col2:
            # Display analysis using expanders
            st.markdown("#### Analysis Details:")
            with st.expander(f"✅ Strengths ({len(result['strengths'])}) - Keywords Matched"):
                if result['strengths']:
                    st.success("Keywords/Entities found in both JD and Resume:")
                    st.write(sorted(list(result['strengths'])))
                else:
                    st.info("No direct keyword/entity matches found based on JD.")

            with st.expander(f"⚠️ Gaps ({len(result['gaps'])}) - JD Keywords Potentially Missing"):
                 if result['gaps']:
                    st.warning("Keywords/Entities from JD not clearly identified in Resume:")
                    st.write(sorted(list(result['gaps'])))
                 else:
                    st.info("All extracted JD keywords/entities appear to be mentioned in the resume.")

            # Placeholder for detailed comments - requires more advanced NLP/LLM integration
            with st.expander("📝 Placeholder Comments (Based on Keywords)"):
                strengths_preview = f" Demonstrates alignment with: {', '.join(list(result['strengths'])[:3])}..." if result['strengths'] else " Strengths alignment needs review."
                gaps_preview = f" Areas for potential discussion include: {', '.join(list(result['gaps'])[:3])}..." if result['gaps'] else " Appears to cover all key areas."
                st.write(f"**Keyword-Based Fit:** Rating {result['rating']}/5 ({result['score']:.1f}% match).{strengths_preview}{gaps_preview}")
                st.caption("_Note: This analysis is based on keyword matching and does not assess experience depth, context, or soft skills. Manual review is essential._")

        st.markdown("---") # Separator between candidates


elif process_button:
    if not jd_text_final:
        st.warning("⚠️ Please provide the Job Description text or upload a JD file.")
    if not resume_files:
        st.warning("⚠️ Please upload at least one resume file.")
else:
    st.info("1. Upload/Paste Job Description. \n2. Upload Resumes. \n3. Click 'Analyze Resumes'.")
