import streamlit as st
import spacy
import io
import re
from docx import Document
import PyPDF2
import pandas as pd # Using pandas for a structured output table

# --- SpaCy Model Loading ---
MODEL_NAME = "en_core_web_sm"

@st.cache_resource
def load_spacy_model(model_name: str):
    """Loads the spaCy model."""
    try:
        nlp = spacy.load(model_name)
        st.success(f"Successfully loaded spaCy model: {model_name}")
        return nlp
    except OSError:
        st.error(f"SpaCy model '{model_name}' not found. It might not have been installed correctly.")
        st.info("Please ensure 'en_core_web_sm' or its wheel file URL is in your requirements.txt and check the deployment logs.")
        st.stop()
    except Exception as e:
         st.error(f"An unexpected error occurred during model loading: {e}")
         st.stop()

nlp = load_spacy_model(MODEL_NAME)

# --- Text Extraction Functions ---

def extract_text_from_pdf(file_obj):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        if len(reader.pages) > 0:
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip() if text else None
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(file_obj):
    text = ""
    try:
        document = Document(file_obj)
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
        return text.strip() if text else None
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {e}")
        return None

def clean_text(text):
    """Basic text cleaning."""
    if not text:
        return ""
    text = text.lower()
    # Remove punctuation, keeping spaces, periods, hyphens, plus signs (for 5+)
    text = re.sub(r'[^a-z0-9\s.\-+#]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Enhanced JD Requirement Extraction and Categorization ---

def extract_and_categorize_requirements(jd_text):
    """
    Extracts potential requirements from JD text and categorizes them.
    This is a more structured approach than simple keywords.
    """
    if not jd_text:
        return {}

    cleaned_jd_text = clean_text(jd_text)
    doc = nlp(cleaned_jd_text)

    # Define categories and associated keywords/phrases (Expand this list!)
    categories = {
        "Years of Experience": ["years experience", "year experience", "yrs experience", "yrs exp", "year+"], # Need to handle numbers intelligently
        "Core Security Tools": ["SkyHigh", "Trellix", "McAfee Web Gateway", "FireEye", "Palo Alto", "Trend Micro", "Zscaler"],
        "SIEM / Threat Detection": ["SIEM", "QRadar", "Sentinel", "Splunk", "EDR", "threat detection", "threat hunting", "alerting", "monitoring"],
        "Network / Infra Security": ["DMZ", "proxy", "routing", "SSL/TLS", "VPN", "firewall", "IDS/IPS", "network security", "infrastructure security", "cisco"],
        "Vulnerability / Risk Mgmt": ["vulnerability assessment", "risk assessment", "risk management", "vulnerability management", "qualys", "nessus", "rapid7", "gRC"],
        "Cloud Security": ["cloud security", "aws security", "azure security", "gcp security", "CASB"],
        "Certifications": ["CISSP", "CCNA", "CEH", "OSCP", "Security+", "Fortinet NSE", "Microsoft Certified", "ISO 27001 Auditor"],
        "Programming / Scripting": ["Python", "Bash", "Shell", "PowerShell", "scripting", "automation", "API", "KQL", "Regex"],
        "Audit / Compliance": ["audit", "compliance", "ISO 27001", "NIST", "SOC 2", "frameworks", "regulatory"],
        "Incident Response / Forensics": ["incident response", "forensics", "malware analysis", "CSIRT", "playbooks"],
        "Communication / Soft Skills": ["communication", "teamwork", "collaboration", "stakeholders", "written", "verbal", "leadership", "mentoring"],
        "Architecture / Design": ["architecture", "design", "planning", "strategy", "SME", "solution"],
        "Deployment / Operations": ["deployment", "implementation", "operate", "manage", "configure", "maintain", "lifecycle", "refresh", "troubleshoot"],
        # Add more categories and keywords relevant to Threat Engineering
    }

    # Attempt to find relevant phrases/keywords for each category in the JD
    jd_requirements = {category: [] for category in categories}

    # Process the JD text with spaCy
    jd_doc = nlp(cleaned_jd_text)

    # Simple check for keywords within categories
    for category, keywords in categories.items():
        found_in_category = set()
        for keyword in keywords:
            # Use case-insensitive simple check for presence
            if keyword.lower() in cleaned_jd_text:
                found_in_category.add(keyword)

            # Also check noun chunks for multi-word terms related to categories
            for chunk in jd_doc.noun_chunks:
                 chunk_text = clean_text(chunk.text)
                 # Simple heuristic: if chunk contains a keyword from the category
                 if any(k.lower() in chunk_text for k in keywords) and chunk_text not in found_in_category:
                      if len(chunk_text) > 3 and chunk_text not in nlp.Defaults.stop_words:
                           found_in_category.add(chunk_text)

            # Check entities that might fit categories
            for ent in jd_doc.ents:
                 ent_text = clean_text(ent.text)
                 if ent.label_ in ["ORG", "PRODUCT", "SKILL", "CERTIFICATION"] and ent_text not in found_in_category: # Assuming SKILL/CERTIFICATION entities exist or using a custom pipeline
                     # Simple check if entity text contains a keyword (might need refinement)
                     if any(k.lower() in ent_text for k in keywords) or category in ["Core Security Tools", "Certifications"]:
                          if len(ent_text) > 2 and ent_text not in nlp.Defaults.stop_words:
                            found_in_category.add(ent_text)


        jd_requirements[category] = sorted(list(found_in_category))

    # --- Special Handling for Years of Experience (Basic) ---
    # This requires more complex regex or pattern matching to be accurate
    exp_matches = re.findall(r'(\d+)\s*years?\s*experience', cleaned_jd_text)
    if exp_matches:
        # Just add a placeholder requirement for now
        max_years = max([int(y) for y in exp_matches])
        jd_requirements["Years of Experience"].insert(0, f"{max_years}+ years experience")
    elif any(word in cleaned_jd_text for word in ["senior", "lead"]):
         if not jd_requirements["Years of Experience"]:
              jd_requirements["Years of Experience"].append("5+ years experience (implied)")


    # Remove categories with no identified requirements
    jd_requirements = {k: v for k, v in jd_requirements.items() if v}

    return jd_requirements


# --- Resume Analysis, Scoring, and Gap Analysis ---

def analyze_and_score_resume(resume_text, jd_requirements):
    """
    Analyzes resume text against categorized JD requirements, calculates score,
    and identifies strengths and gaps.
    """
    if not resume_text or not jd_requirements:
        return {}, 0, {}, {}

    cleaned_resume_text = clean_text(resume_text)

    category_scores = {}
    strengths = {}
    gaps = {}
    total_possible_requirements = 0
    total_matched_requirements = 0

    for category, requirements in jd_requirements.items():
        strengths[category] = []
        gaps[category] = []
        matched_in_category = 0
        total_in_category = len(requirements)
        total_possible_requirements += total_in_category

        for req in requirements:
            # Simple check for presence of the requirement phrase/keyword in resume
            if req.lower() in cleaned_resume_text:
                strengths[category].append(req)
                matched_in_category += 1
                total_matched_requirements += 1
            else:
                gaps[category].append(req)

        # Simple category score based on percentage match in that category
        category_scores[category] = (matched_in_category / total_in_category) * 100 if total_in_category > 0 else 0

    # Overall score based on total matched requirements
    overall_score = (total_matched_requirements / total_possible_requirements) * 100 if total_possible_requirements > 0 else 0

    return category_scores, overall_score, strengths, gaps

def analyze_soft_skills(resume_text):
    """Basic check for soft skill keywords."""
    if not resume_text:
        return []

    cleaned_text = clean_text(resume_text)
    soft_skill_keywords = [
        "communication", "collaborate", "teamwork", "leadership",
        "problem-solving", "adaptable", "proactive", "articulate",
        "present", "negotiate", "manage", "mentor", "stakeholders"
    ]
    found_skills = [skill for skill in soft_skill_keywords if skill in cleaned_text]
    return sorted(list(set(found_skills))) # Return unique found skills


# --- Streamlit App Interface ---

st.title("🛡️ Threat Engineer Resume Screener (Detailed Analysis)")

st.write("Upload a Job Description and a Candidate Resume (PDF or DOCX) for a detailed analysis.")

# File Uploaders
jd_file = st.file_uploader("Upload Job Description (PDF or DOCX)", type=["pdf", "docx"], key="jd_uploader")
resume_file = st.file_uploader("Upload Candidate Resume (PDF or DOCX)", type=["pdf", "docx"], key="resume_uploader")

# Screening Threshold (optional)
screening_threshold = st.slider("Set 'Screened In' Score Threshold (%)", 0, 100, 60)

analyze_button = st.button("Perform Detailed Analysis")

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
                st.error("Could not extract text from the Job Description file. Please check the file format.")
            elif not resume_text:
                st.error("Could not extract text from the Candidate Resume file. Please check the file format.")
            else:
                # --- Analysis ---
                jd_requirements = extract_and_categorize_requirements(jd_text)

                if not any(jd_requirements.values()):
                     st.warning("Could not identify specific requirements from the Job Description.")
                     st.info("Consider enhancing the `extract_and_categorize_requirements` function with more keywords/patterns relevant to your JDs.")
                     st.stop()

                category_scores, overall_score, strengths, gaps = analyze_and_score_resume(resume_text, jd_requirements)
                found_soft_skills = analyze_soft_skills(resume_text)


                # --- Display Results ---
                st.subheader("📊 Overall Analysis Results")

                st.write(f"**Overall Match Score:** {overall_score:.2f}%")

                # Screening Decision
                if overall_score >= screening_threshold:
                    st.success(f"✅ Candidate Screened In (Overall Score >= {screening_threshold}%)")
                else:
                    st.warning(f"❌ Candidate Not Screened In (Overall Score < {screening_threshold}%)")

                # --- Detailed Breakdown ---
                st.subheader("🔍 Detailed Breakdown by Category")

                if category_scores:
                    # Prepare data for a table
                    breakdown_data = []
                    for category, score in category_scores.items():
                        breakdown_data.append({
                            "Category": category,
                            "Match Score (%)": f"{score:.2f}%",
                            "Found Items": ", ".join(strengths[category]) if strengths[category] else "None",
                            "Missing Items (Gaps)": ", ".join(gaps[category]) if gaps[category] else "None"
                        })
                    df = pd.DataFrame(breakdown_data)
                    st.dataframe(df, hide_index=True)
                else:
                    st.info("No categories could be analyzed.")


                # --- Soft Skills Assessment ---
                st.subheader("🧠 Soft Skills Assessment (Basic)")
                if found_soft_skills:
                    st.write("Potential soft skills identified based on keywords:")
                    st.write(", ".join(found_soft_skills))
                else:
                    st.info("No common soft skill keywords identified.")
                st.caption("_Based on keyword presence, not contextual understanding._")


                # --- Transparent Feedback ---
                st.subheader("📝 Transparent Feedback")
                if overall_score >= screening_threshold:
                    st.write("Based on the analysis of the Job Description and Resume:")
                    st.write("The candidate demonstrates a strong alignment with the requirements, achieving a match score above the screening threshold.")
                    if any(strengths.values()):
                         st.write("Key areas of strength identified:")
                         # Display strengths from categories that had matches
                         for category, items in strengths.items():
                              if items:
                                   st.markdown(f"- **{category}:** {', '.join(items)}")
                    else:
                        st.write("Overall, the resume appears to align well with the JD requirements.")

                else:
                    st.write("Based on the analysis of the Job Description and Resume:")
                    st.write(f"The candidate's resume match score ({overall_score:.2f}%) is below the screening threshold ({screening_threshold}%).")
                    if any(gaps.values()):
                        st.write("Areas where the resume did not clearly demonstrate requirements found in the Job Description include:")
                        # Display gaps from categories that had missing items
                        for category, items in gaps.items():
                             if items:
                                  st.markdown(f"- **{category}:** {', '.join(items)}")
                    else:
                        st.write("Analysis indicates a general lack of specific keywords/phrases found in the Job Description.")

                st.markdown("---")
                st.markdown("_**Note:** This tool provides an automated assessment based on identifiable keywords and phrases. It is not a substitute for a thorough human review._")


                # Optional: Show extracted text (useful for debugging)
                with st.expander("Show Extracted Text (for debugging)"):
                    if jd_text:
                        st.subheader("Job Description Text:")
                        st.text(jd_text[:3000] + ("..." if len(jd_text) > 3000 else ""))
                    if resume_text:
                        st.subheader("Resume Text:")
                        st.text(resume_text[:3000] + ("..." if len(resume_text) > 3000 else ""))
