import streamlit as st
import spacy
import subprocess
import sys
import io
from docx import Document
import PyPDF2

# --- SpaCy Model Loading and Download Logic ---
# Define the spaCy model name
MODEL_NAME = "en_core_web_sm"

@st.cache_resource # Use st.cache_resource for caching models/connections
def load_spacy_model(model_name: str):
    """
    Loads the spaCy model, downloading it if necessary.
    Uses st.cache_resource to cache the model in memory.
    """
    try:
        # Try loading the model
        nlp = spacy.load(model_name)
        st.success(f"Successfully loaded spaCy model: {model_name}")
        return nlp
    except OSError:
        # If the model is not found (OSError), attempt to download it
        st.warning(f"SpaCy model '{model_name}' not found. Attempting to download...")
        try:
            # Execute the spacy download command using subprocess
            # Use sys.executable to ensure the command runs with the correct Python interpreter
            subprocess.check_call([sys.executable, "-m", "spacy", "download", model_name])
            st.success(f"Successfully downloaded spaCy model: {model_name}")
            # Try loading the model again after successful download
            nlp = spacy.load(model_name)
            return nlp
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to download spaCy model '{model_name}'. Error: {e}")
            st.info("Please check your internet connection or try again later.")
            st.stop() # Stop the app execution if model cannot be loaded
        except Exception as e:
             st.error(f"An unexpected error occurred during model download/loading: {e}")
             st.stop()

# Load the spaCy model using the cached function
nlp = load_spacy_model(MODEL_NAME)

# --- Resume Text Extraction Functions ---

def extract_text_from_pdf(file_obj):
    """Extracts text from a PDF file object."""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(file_obj):
    """Extracts text from a DOCX file object."""
    try:
        document = Document(file_obj)
        text = ""
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {e}")
        return None

# --- Streamlit App Interface ---

st.title("Threat Engineer Resume Screener")

st.write("Upload a resume (PDF or DOCX) to analyze.")

uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])

if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1].lower()
    resume_text = None

    # Read the file content into a BytesIO object for compatibility with readers
    file_bytes = io.BytesIO(uploaded_file.getvalue())

    if file_extension == "pdf":
        resume_text = extract_text_from_pdf(file_bytes)
    elif file_extension == "docx":
        resume_text = extract_text_from_docx(file_bytes)
    else:
        st.error("Unsupported file type.")

    if resume_text:
        st.subheader("Extracted Text:")
        st.text(resume_text[:1000] + ("..." if len(resume_text) > 1000 else "")) # Display first 1000 chars

        # --- SpaCy Processing (Example) ---
        st.subheader("SpaCy Analysis (Example):")
        with st.spinner("Analyzing text..."):
            doc = nlp(resume_text)

        # Example: Extract Named Entities
        st.write("Named Entities:")
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        if entities:
            st.write(entities)
        else:
            st.write("No named entities found.")

        # Example: Extract Nouns (potential keywords)
        st.write("Nouns (Potential Keywords):")
        nouns = [token.text for token in doc if token.pos_ == "NOUN"]
        st.write(list(set(nouns))[:50]) # Display up to 50 unique nouns

        # --- Add your specific screening logic here ---
        st.subheader("Screening Results:")
        # You would add your custom logic here to identify relevant skills,
        # experience, and qualifications for a Threat Engineer role based on 'doc'
        # For example:
        # required_skills = ["penetration testing", "vulnerability assessment", "SIEM", "firewalls"]
        # found_skills = [skill for skill in required_skills if skill.lower() in resume_text.lower()]
        # st.write(f"Required skills found: {', '.join(found_skills)}")
        st.info("Implement your specific Threat Engineer screening logic here using the processed 'doc' object.")
