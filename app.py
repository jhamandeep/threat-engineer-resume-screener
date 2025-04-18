import streamlit as st
import spacy
import io
from docx import Document
import PyPDF2
# No need for subprocess and sys anymore

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
        # Try loading the model
        nlp = spacy.load(model_name)
        st.success(f"Successfully loaded spaCy model: {model_name}")
        return nlp
    except OSError:
        # If loading fails, it means the model wasn't installed correctly
        st.error(f"SpaCy model '{model_name}' not found. It might not have been installed correctly.")
        st.info("Please ensure 'en_core_web_sm' or its wheel file URL is in your requirements.txt and check the deployment logs.")
        st.stop() # Stop the app execution if model cannot be loaded
    except Exception as e:
         st.error(f"An unexpected error occurred during model loading: {e}")
         st.stop()


# Load the spaCy model using the cached function
nlp = load_spacy_model(MODEL_NAME)

# --- Resume Text Extraction Functions ---

def extract_text_from_pdf(file_obj):
    """Extracts text from a PDF file object."""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text = ""
        # Check if reader has pages before iterating
        if len(reader.pages) > 0:
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                # Ensure page extraction is successful
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    # Handle pages that might not have extractable text (e.g., images)
                    text += "[Could not extract text from this page]\n"
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
        resume_text = None # Ensure resume_text is None for unsupported types

    if resume_text:
        st.subheader("Extracted Text:")
        # Display only a part of the text if it's very long
        display_text = resume_text.strip()
        if len(display_text) > 1500: # Increased display limit slightly
             st.text(display_text[:1500] + "...\n[Text truncated for display]")
        else:
            st.text(display_text)


        # --- SpaCy Processing (Example) ---
        st.subheader("SpaCy Analysis (Example):")
        with st.spinner("Analyzing text..."):
            try:
                doc = nlp(resume_text)
                analysis_successful = True
            except Exception as e:
                 st.error(f"Error during spaCy processing: {e}")
                 analysis_successful = False


        if analysis_successful:
            # Example: Extract Named Entities
            st.write("Named Entities (PERSON, ORG, GPE, etc.):")
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            if entities:
                # Display entities in a more readable format
                for text, label in entities:
                    st.text(f"- {text} ({label})")
            else:
                st.write("No significant named entities found.")

            # Example: Extract Skills (requires a custom spaCy pipeline or pattern matching)
            # SpaCy's base models don't have a 'SKILL' entity out of the box.
            # You would typically use a library like spacy-lookups-data or build custom patterns.
            st.write("Potential Skills (Basic Noun/Verb Phrase Extraction - Needs Improvement):")
            # This is a very basic example; real skill extraction is more complex.
            skills_candidates = [chunk.text for chunk in doc.noun_chunks] # Example: Noun chunks
            st.write(list(set(skills_candidates))[:30]) # Display up to 30 unique noun chunks


            # --- Add your specific screening logic here ---
            st.subheader("Threat Engineer Screening Summary:")
            st.info("Integrate your specific logic here to match resume content against Threat Engineer requirements.")
            # Example: Check for keywords
            keywords = ["penetration testing", "vulnerability assessment", "SIEM", "firewall", "IDS", "IPS", "malware analysis", "incident response"]
            found_keywords = [keyword for keyword in keywords if keyword.lower() in resume_text.lower()]
            if found_keywords:
                st.write("Relevant keywords found:")
                st.write(", ".join(found_keywords))
            else:
                 st.write("No specific Threat Engineer keywords found.")

    elif uploaded_file is not None:
         # Handle cases where file was uploaded but text extraction failed
         st.warning("Could not process the file.")

# Optional: Add some instructions or notes
st.markdown("---")
st.markdown("This app uses spaCy for natural language processing.")
