import os
import io
import re
import json
import time
import random
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.express as px
import pypdf
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Configuration & State
# ---------------------------------------------------------
st.set_page_config(
    page_title="MatchPro ATS — Recruiter Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"

if "ats_results" not in st.session_state:
    st.session_state.ats_results = None

# ---------------------------------------------------------
# Dual Theme Dynamic Styling Engine
# ---------------------------------------------------------
if st.session_state.theme_mode == "Dark":
    theme_css = """
    <style>
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        .hero-container {
            padding: 1.8rem 2rem;
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            border: 1px solid #30363d;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .hero-subtitle { color: #8b949e !important; font-size: 0.95rem; margin-top: 0.3rem; }

        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #c9d1d9 !important; }

        .metric-card {
            background-color: #161b22 !important;
            border: 1px solid #30363d !important;
            border-radius: 12px;
            padding: 1.1rem;
            text-align: center;
        }
        .metric-value { font-size: 1.7rem; font-weight: 700; color: #f0f6fc !important; }
        .metric-label { font-size: 0.8rem; color: #8b949e !important; text-transform: uppercase; letter-spacing: 0.5px; }

        .diff-card {
            background-color: #161b22 !important;
            border: 1px solid #2d333b !important;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.8rem;
        }
        .text-before { color: #fb7185 !important; font-size: 0.88rem; font-family: monospace; }
        .text-after { color: #4ade80 !important; font-size: 0.88rem; font-family: monospace; font-weight: 600; }

        .badge { display: inline-block; padding: 0.22rem 0.65rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; margin: 0.2rem; }
        .badge-matched { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-partial { background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-missing { background-color: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-free { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-paid { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

        /* Dark Mode Textarea */
        textarea, .stTextArea textarea {
            background-color: #161b22 !important;
            color: #f0f6fc !important;
            border: 1px solid #30363d !important;
            border-radius: 8px !important;
        }

        /* Dark Mode Theme Dropdown */
        div[data-baseweb="select"] > div {
            background-color: #161b22 !important;
            color: #f0f6fc !important;
            border: 1px solid #30363d !important;
        }
        div[data-baseweb="select"] * { color: #f0f6fc !important; }

        /* Dark Mode File Uploader & Uploaded Items */
        [data-testid="stFileUploader"] {
            background-color: #161b22 !important;
            border: 1px dashed #30363d !important;
            border-radius: 10px !important;
            padding: 0.8rem !important;
        }
        [data-testid="stFileUploader"] section {
            background-color: #161b22 !important;
        }
        [data-testid="stFileUploaderFile"] {
            background-color: #21262d !important;
            border: 1px solid #30363d !important;
            border-radius: 8px !important;
        }
        [data-testid="stFileUploaderFile"] * {
            color: #f0f6fc !important;
        }
        [data-testid="stFileUploader"] * {
            color: #c9d1d9 !important;
        }

        /* Dark Mode Expander */
        div[data-testid="stExpander"] {
            background-color: #161b22 !important;
            border: 1px solid #30363d !important;
            border-radius: 10px !important;
        }
        div[data-testid="stExpander"] details, div[data-testid="stExpander"] summary {
            background-color: #161b22 !important;
            color: #f0f6fc !important;
        }
        div[data-testid="stExpander"] summary * { color: #f0f6fc !important; }

        button[data-baseweb="tab"] { color: #8b949e !important; }
        button[data-baseweb="tab"][aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }

        div.stButton > button:first-child {
            background: linear-gradient(90deg, #2563eb, #3b82f6);
            color: #ffffff !important;
            font-weight: 700;
            border: none;
            border-radius: 8px;
        }
    </style>
    """
else:
    theme_css = """
    <style>
        .stApp { background-color: #f8fafc !important; color: #0f172a !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        .hero-container {
            padding: 1.8rem 2rem;
            background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        }
        .hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            background: linear-gradient(90deg, #0284c7, #4f46e5, #9333ea);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .hero-subtitle { color: #475569 !important; font-size: 0.95rem; margin-top: 0.3rem; font-weight: 500; }

        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #0f172a !important; }

        .metric-card {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px;
            padding: 1.1rem;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }
        .metric-value { font-size: 1.7rem; font-weight: 700; color: #0f172a !important; }
        .metric-label { font-size: 0.8rem; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }

        .diff-card {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
        .text-before { color: #be123c !important; font-size: 0.88rem; font-family: monospace; font-weight: 600; }
        .text-after { color: #15803d !important; font-size: 0.88rem; font-family: monospace; font-weight: 600; }

        .badge { display: inline-block; padding: 0.22rem 0.65rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; margin: 0.2rem; }
        .badge-matched { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-partial { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-missing { background-color: #ffe4e6; color: #be123c; border: 1px solid #fca5a5; }
        .badge-free { background-color: #ecfdf5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-paid { background-color: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }

        /* Light Mode Textarea */
        textarea, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }

        /* Light Mode Theme Dropdown */
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        div[data-baseweb="select"] * { color: #0f172a !important; }

        /* Light Mode File Uploader & Uploaded Items */
        [data-testid="stFileUploader"] {
            background-color: #ffffff !important;
            border: 2px dashed #cbd5e1 !important;
            border-radius: 10px !important;
            padding: 0.9rem !important;
        }
        [data-testid="stFileUploader"] section {
            background-color: #f8fafc !important;
        }
        [data-testid="stFileUploaderFile"] {
            background-color: #f1f5f9 !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }
        [data-testid="stFileUploaderFile"] * {
            color: #0f172a !important;
        }
        [data-testid="stFileUploader"] * {
            color: #1e293b !important;
        }

        /* Light Mode Expander */
        div[data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
        }
        div[data-testid="stExpander"] details, div[data-testid="stExpander"] summary {
            background-color: #ffffff !important;
            color: #0f172a !important;
        }
        div[data-testid="stExpander"] summary * { color: #0f172a !important; }

        button[data-baseweb="tab"] { color: #64748b !important; }
        button[data-baseweb="tab"][aria-selected="true"] { color: #0284c7 !important; border-bottom-color: #0284c7 !important; }

        div.stButton > button:first-child {
            background: linear-gradient(90deg, #0284c7, #2563eb);
            color: #ffffff !important;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(2, 132, 199, 0.25);
        }
    </style>
    """
st.markdown(theme_css, unsafe_allow_html=True)

# ---------------------------------------------------------
# Secrets & API Key Resolution
# ---------------------------------------------------------
load_dotenv()

GEMINI_API_KEY = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not GEMINI_API_KEY:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ `GEMINI_API_KEY` is missing. Configure it in Streamlit Cloud Secrets or `.env` file.")
    st.stop()

@st.cache_resource
def get_ai_client(api_key: str):
    return genai.Client(api_key=api_key)

ai_client = get_ai_client(GEMINI_API_KEY)

# ---------------------------------------------------------
# Document Extraction Engines
# ---------------------------------------------------------
def extract_docx_native(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            xml_content = docx_zip.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [node.text for node in tree.iterfind('.//w:t', namespaces) if node.text]
            return " ".join(texts)
    except Exception:
        return ""

def extract_text(file_bytes: bytes, filename: str) -> tuple[str, bool]:
    filename_lower = filename.lower()
    text = ""
    try:
        if filename_lower.endswith(".pdf"):
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif filename_lower.endswith(".docx"):
            text = extract_docx_native(file_bytes)
        elif filename_lower.endswith(".doc"):
            raw = file_bytes.decode("latin-1", errors="ignore")
            blocks = re.findall(r'[a-zA-Z0-9.,;:!?/@#%&()\-_+=\n ]{4,}', raw)
            text = " ".join([b.strip() for b in blocks if len(b.strip()) > 3])
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return "", False

    cleaned = text.strip()
    return cleaned, len(cleaned) >= 50

# ---------------------------------------------------------
# Resilient API Call with Intelligent 429 Quota Backoff
# ---------------------------------------------------------
def clean_json_string(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()

def generate_with_resilience(prompt: str) -> str:
    candidate_models = ["gemini-3.6-flash"]
    attempts_log = []

    for model_name in candidate_models:
        for attempt in range(4):
            try:
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                err_msg = str(e)
                attempts_log.append(f"{model_name} (Attempt {attempt + 1}): {err_msg}")
                
                # Check if Google specified a retry delay for 429 quota exhaustion
                retry_match = re.search(r"retry in ([\d\.]+)s", err_msg, re.IGNORECASE)
                if not retry_match:
                    retry_match = re.search(r"'retryDelay': '(\d+)s'", err_msg)
                
                if retry_match:
                    sleep_time = float(retry_match.group(1)) + 2.0
                elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    sleep_time = 25.0 + random.uniform(1.0, 3.0)
                else:
                    sleep_time = (2 ** attempt) + random.uniform(1.0, 2.0)

                time.sleep(sleep_time)

    summary_err = "\n".join(attempts_log[-3:])
    raise RuntimeError(f"API request could not complete after multiple retries:\n{summary_err}")

# ---------------------------------------------------------
# UI Header & Theme Switcher
# ---------------------------------------------------------
top_col1, top_col2 = st.columns([5, 1])
with top_col1:
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">⚡ MatchPro ATS Intelligence Engine</h1>
        <p class="hero-subtitle">Multi-Resume Benchmarking • Precise From-To Phrasing Audits • Work & Project Upgrades</p>
    </div>
    """, unsafe_allow_html=True)
with top_col2:
    selected_theme = st.selectbox("🎨 UI Theme", ["Dark", "Light"], index=0 if st.session_state.theme_mode == "Dark" else 1)
    if selected_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = selected_theme
        st.rerun()

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 1. Target Job Description")
    jd_input = st.text_area(
        label="JD Input",
        label_visibility="collapsed",
        height=280,
        placeholder="Paste target job requirements, mandatory tools, frameworks, minimum experience, and qualifications..."
    )

with col_right:
    st.markdown("### 📁 2. Upload Candidate Resumes")
    uploaded_files = st.file_uploader(
        label="Resume Upload",
        label_visibility="collapsed",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True
    )
    if uploaded_files:
        st.info(f"📄 Staged **{len(uploaded_files)}** candidate resume(s).")

col_btn, col_reset = st.columns([4, 1])
with col_btn:
    analyze_btn = st.button("🚀 Run Comprehensive ATS & Resume Overhaul", use_container_width=True)
with col_reset:
    if st.button("🧹 Reset", use_container_width=True):
        st.session_state.ats_results = None
        st.rerun()

# ---------------------------------------------------------
# Evaluation Workflow
# ---------------------------------------------------------
if analyze_btn:
    if not jd_input.strip():
        st.warning("⚠️ Please provide a target Job Description first.")
        st.stop()
    if not uploaded_files:
        st.warning("⚠️ Please upload at least one candidate resume.")
        st.stop()
    if len(uploaded_files) > 5:
        st.warning("⚠️ Maximum 5 resumes allowed per batch to preserve API rate limits.")
        st.stop()

    with st.spinner("⚡ Evaluating profiles, phrasing fixes, project descriptions, and experience..."):
        payload = ""
        skipped_files = []

        for file in uploaded_files:
            file_bytes = file.read()
            extracted_text, is_valid = extract_text(file_bytes, file.name)
            
            if not is_valid:
                skipped_files.append(file.name)
                continue
            
            payload += f"\n--- CANDIDATE: {file.name} ---\n{extracted_text[:11000]}\n"

        if skipped_files:
            st.error(f"⚠️ Unreadable/scanned documents detected: {', '.join(skipped_files)}.")

        if not payload.strip():
            st.stop()

        prompt = f"""
You are an expert ATS recruitment evaluator and technical resume coach.
Analyze each candidate strictly against the Job Description AND conduct a practical resume improvement audit.

JOB DESCRIPTION:
{jd_input}

RESUMES:
{payload}

Return ONLY valid JSON matching this schema:
{{
  "candidates": [
    {{
      "name": "Candidate Name or Filename",
      "score": 78
    }}
  ],
  "reports": [
    {{
      "name": "Candidate Name",
      "score": 78,
      "score_category": "Strong Match",
      "score_breakdown": {{
        "skills": "32.0 / 40.0",
        "experience": "22.0 / 25.0",
        "projects": "11.0 / 15.0",
        "education": "9.0 / 10.0",
        "keywords": "8.0 / 10.0"
      }},
      "skills": {{
        "matched": ["Python", "Docker", "SQL", "Git"],
        "partial": ["Kubernetes"],
        "missing": ["AWS ECS", "Kafka", "Redis"]
      }},
      "experience_match": "Required: 3+ years | Candidate: 3.5 years | Status: MATCHED",
      "education_match": "Required: B.Tech in CS/IT | Candidate: B.Tech CSE | Status: MATCHED",
      "gaps": [
        "Message queues and streaming missing from candidate skillset.",
        "No in-memory caching mentioned in recent work."
      ],
      "link_and_contact_audit": {{
        "current_placement": "LinkedIn and GitHub are listed as plain text at the bottom.",
        "recommended_placement": "Place clean clickable handles in the top header below name and contact info.",
        "reasoning": "Recruiters and ATS parsers expect links in the top header for fast profile verification."
      }},
      "phrasing_and_grammar_fixes": [
        {{
          "category": "Spelling / Typo",
          "from_text": "Built web apis using Postgress and Flsak.",
          "to_text": "Built web APIs using PostgreSQL and Flask.",
          "reasoning": "Corrects framework typos that cause ATS keyword filter drops."
        }},
        {{
          "category": "Action Verb Upgrade",
          "from_text": "Responsible for managing bug fixes and API calls.",
          "to_text": "Streamlined backend API response times and resolved critical application defects.",
          "reasoning": "Converts passive task lists into action-oriented delivery statements."
        }}
      ],
      "role_upgrade_suggestions": [
        {{
          "current_title": "Software Developer Intern",
          "recommended_title": "Backend Engineering Intern",
          "reasoning": "More descriptive title directly aligned with target role."
        }}
      ],
      "work_experience_improvements": [
        {{
          "company_or_role": "Web Development Intern at XYZ Corp",
          "mistake_identified": "Only listed routine daily duties without showing metrics or tech tools.",
          "from_bullet": "Worked on frontend designs and tested features.",
          "to_bullet": "Developed responsive user interface components with React and implemented client-side state handling to improve page load speed.",
          "hiring_tip": "Highlight concrete tooling used and team collaboration to appeal to product companies."
        }}
      ],
      "project_improvements": [
        {{
          "project_name": "Project Name from Resume",
          "candidate_original_description": "Candidate summary as written in the resume.",
          "context_feedback": "Explain how clearly the project conveys problem context and scope.",
          "from_bullet": "Original bullet point from resume.",
          "to_bullet": "Rewritten bullet point preserving actual stack with stronger action verbs.",
          "presentation_tip": "Advice on showcasing this project (e.g. adding live demo or metrics)."
        }}
      ],
      "certifications": {{
        "free_certifications": [
          {{"title": "freeCodeCamp Back End Development and APIs", "url": "[https://www.freecodecamp.org/learn/back-end-development-and-apis/](https://www.freecodecamp.org/learn/back-end-development-and-apis/)", "desc": "Covers Node.js, Express, and microservice fundamentals."}},
          {{"title": "CS50 Introduction to Computer Science", "url": "[https://www.edx.org/cs50](https://www.edx.org/cs50)", "desc": "Solid foundation in data structures, algorithms, and memory management."}}
        ],
        "paid_certification": {{
          "title": "AWS Certified Solutions Architect – Associate (SAA-C03)",
          "cost": "~$150 USD",
          "desc": "Industry-standard credential validating scalable cloud architecture and deployment practices."
        }}
      }}
    }}
  ]
}}
"""
        try:
            raw_response = generate_with_resilience(prompt)
            clean_json = clean_json_string(raw_response)
            data = json.loads(clean_json)
            st.session_state.ats_results = {
                "candidates": data.get("candidates", []) if isinstance(data, dict) else [],
                "reports": data.get("reports", []) if isinstance(data, dict) else []
            }
        except Exception as e:
            st.error(f"Analysis interrupted: {e}")

# ---------------------------------------------------------
# Presentation & Drill-Down Layer
# ---------------------------------------------------------
if st.session_state.ats_results:
    results = st.session_state.ats_results
    candidates = results.get("candidates", [])
    reports = results.get("reports", [])

    st.markdown("---")
    
    if candidates:
        top_candidate = max(candidates, key=lambda x: x.get("score", 0))
        avg_score = round(sum(c.get("score", 0) for c in candidates) / len(candidates), 1)
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(candidates)}</div>
                <div class="metric-label">Resumes Analyzed</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #38bdf8;">{str(top_candidate.get('name', 'N/A'))[:14]}</div>
                <div class="metric-label">Top Candidate</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #22c55e;">{top_candidate.get('score', 0)}%</div>
                <div class="metric-label">Highest Score</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_score}%</div>
                <div class="metric-label">Batch Average</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        df = pd.DataFrame(candidates).sort_values(by="score", ascending=True)
        fig = px.bar(
            df,
            x="score",
            y="name",
            orientation="h",
            text="score",
            labels={"score": "ATS Match Score (%)", "name": "Candidate"},
            color="score",
            color_continuous_scale=["#f43f5e", "#38bdf8", "#22c55e"],
            range_x=[0, 100]
        )
        fig.update_traces(texttemplate='<b>%{text}%</b>', textposition='outside', marker=dict(line=dict(width=0)))
        
        paper_bg = "#0d1117" if st.session_state.theme_mode == "Dark" else "#ffffff"
        plot_bg = "#161b22" if st.session_state.theme_mode == "Dark" else "#f8fafc"
        font_col = "#c9d1d9" if st.session_state.theme_mode == "Dark" else "#0f172a"
        grid_col = "#21262d" if st.session_state.theme_mode == "Dark" else "#cbd5e1"

        fig.update_layout(
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
            font=dict(color=font_col),
            height=280 + (len(candidates) * 45),
            margin=dict(l=20, r=40, t=20, b=20),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor=grid_col),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Benchmark to CSV",
            data=csv_data,
            file_name="ats_benchmark_report.csv",
            mime="text/csv"
        )

    st.markdown("### 📋 Candidate Evaluation Drill-Down")

    for rep in reports:
        if not isinstance(rep, dict):
            continue
        name = rep.get("name", "Candidate")
        score = rep.get("score", 0)
        badge_style = "badge-matched" if score >= 75 else "badge-partial" if score >= 50 else "badge-missing"
        badge_label = "Strong Match" if score >= 75 else "Moderate Match" if score >= 50 else "Weak Match"

        with st.expander(f"👤 {name} — Score: {score}% ({badge_label})", expanded=True):
            tab1, tab2, tab3 = st.tabs([
                "🎯 1. ATS Fit & Skill Gaps", 
                "🔍 2. Resume Hygiene & From➔To Audits", 
                "🚀 3. Projects, Work Experience & Certifications"
            ])

            # TAB 1: ATS Scoring & Skills
            with tab1:
                t1_col1, t1_col2 = st.columns([1, 1], gap="medium")
                with t1_col1:
                    st.markdown(f"**Fit Status:** <span class='badge {badge_style}'>{badge_label} ({score}%)</span>", unsafe_allow_html=True)
                    st.markdown("<br>**📈 Weighted Score Breakdown:**", unsafe_allow_html=True)
                    sb = rep.get("score_breakdown", {})
                    if isinstance(sb, dict):
                        for k, v in sb.items():
                            st.write(f"• **{str(k).title()}**: `{v}`")

                    st.markdown("**🎯 Technical Skill Alignment:**")
                    skills = rep.get("skills", {})
                    if isinstance(skills, dict):
                        matched_list = skills.get('matched', [])
                        partial_list = skills.get('partial', [])
                        missing_list = skills.get('missing', [])
                        
                        matched_html = "".join([f"<span class='badge badge-matched'>{s}</span>" for s in (matched_list if isinstance(matched_list, list) else [])]) or "<i>None</i>"
                        partial_html = "".join([f"<span class='badge badge-partial'>{s}</span>" for s in (partial_list if isinstance(partial_list, list) else [])]) or "<i>None</i>"
                        missing_html = "".join([f"<span class='badge badge-missing'>{s}</span>" for s in (missing_list if isinstance(missing_list, list) else [])]) or "<i>None</i>"

                        st.markdown(f"**Matched:**<br>{matched_html}", unsafe_allow_html=True)
                        st.markdown(f"**Partial:**<br>{partial_html}", unsafe_allow_html=True)
                        st.markdown(f"**Missing:**<br>{missing_html}", unsafe_allow_html=True)

                with t1_col2:
                    st.markdown("**⏳ Experience Alignment:**")
                    st.info(str(rep.get('experience_match', 'N/A')))

                    st.markdown("**🎓 Education Fit:**")
                    st.info(str(rep.get('education_match', 'N/A')))

                    st.markdown("**⚠️ Identified Gaps:**")
                    gaps_list = rep.get("gaps", [])
                    if isinstance(gaps_list, list):
                        for gap in gaps_list:
                            st.markdown(f"- {gap}")
                    else:
                        st.markdown(f"- {gaps_list}")

            # TAB 2: Resume Hygiene, Links & Precise From➔To Fixes
            with tab2:
                st.markdown("#### 🔗 Hyperlinks & Profile Placement Audit")
                link_audit = rep.get("link_and_contact_audit", {})
                if not isinstance(link_audit, dict):
                    link_audit = {}
                c_place = link_audit.get('current_placement', 'N/A')
                r_place = link_audit.get('recommended_placement', 'N/A')
                l_reason = link_audit.get('reasoning', '')

                st.markdown(f"""
                <div class="diff-card">
                    <span style="font-weight: 700; color: #fb7185;">❌ Current Placement:</span><br>
                    <span class="text-before">{c_place}</span><br><br>
                    <span style="font-weight: 700; color: #4ade80;">✅ Recommended Placement:</span><br>
                    <span class="text-after">{r_place}</span>
                    <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.5rem; margin-bottom: 0;"><b>Why this matters:</b> {l_reason}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### ✍️ Granular 'From ➔ To' Phrasing & Grammar Transformations")
                fixes = rep.get("phrasing_and_grammar_fixes", [])
                if isinstance(fixes, list) and fixes:
                    for f in fixes:
                        if not isinstance(f, dict):
                            continue
                        cat = f.get("category", "Refinement")
                        from_txt = f.get("from_text", "")
                        to_txt = f.get("to_text", "")
                        reason = f.get("reasoning", "")
                        st.markdown(f"""
                        <div class="diff-card">
                            <span class="badge badge-partial">{cat}</span><br>
                            <span style="font-weight: 600; color: #fb7185;">❌ From (Current):</span><br>
                            <span class="text-before">"{from_txt}"</span><br><br>
                            <span style="font-weight: 600; color: #4ade80;">✅ To (Recommended):</span><br>
                            <span class="text-after">"{to_txt}"</span>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.5rem; margin-bottom: 0;"><b>ATS Impact:</b> {reason}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("✅ Clean text! No obvious grammar or weak phrasing slips detected.")

                st.markdown("#### 🏷️ Recommended Role Title Transformations")
                roles = rep.get("role_upgrade_suggestions", [])
                if isinstance(roles, list) and roles:
                    for r in roles:
                        if not isinstance(r, dict):
                            continue
                        curr = r.get('current_title', 'Current')
                        rec = r.get('recommended_title', 'Recommended')
                        reason = r.get('reasoning', '')
                        st.markdown(f"""
                        <div class="diff-card">
                            <span style="font-weight: 600; color: #fb7185;">❌ Current Role:</span> <b>{curr}</b> ➔ 
                            <span style="font-weight: 600; color: #4ade80;">✅ Upgrade To:</span> <b>{rec}</b>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.4rem; margin-bottom: 0;">{reason}</p>
                        </div>
                        """, unsafe_allow_html=True)

            # TAB 3: Projects, Experience & Balanced Certs
            with tab3:
                st.markdown("#### 🛠️ Project Description Review & Context Polish")
                projects = rep.get("project_improvements", [])
                if isinstance(projects, list) and projects:
                    for proj in projects:
                        if not isinstance(proj, dict):
                            continue
                        p_name = proj.get("project_name", "Project")
                        orig_desc = proj.get("candidate_original_description", "")
                        context_fb = proj.get("context_feedback", "")
                        from_b = proj.get("from_bullet", "")
                        to_b = proj.get("to_bullet", "")
                        tip = proj.get("presentation_tip", "")

                        st.markdown(f"""
                        <div class="diff-card">
                            <h4 style="margin: 0; color: #38bdf8;">📌 {p_name}</h4>
                            <p style="color: #8b949e; font-size: 0.85rem; margin-top: 0.3rem;"><b>Resume Summary:</b> <i>"{orig_desc}"</i></p>
                            <p style="color: #f59e0b; font-size: 0.85rem; margin: 0.3rem 0;"><b>💡 Context & Clarity Review:</b> {context_fb}</p>
                            <b style="font-size: 0.85rem;">Bullet Point Improvement:</b><br>
                            <span class="text-before">❌ From: "{from_b}"</span><br>
                            <span class="text-after">✅ To: "{to_b}"</span><br><br>
                            <p style="color: #4ade80; font-size: 0.85rem; margin: 0;"><b>🎯 Presentation Tip:</b> {tip}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No project description improvements flagged for this candidate.")

                st.markdown("#### 💼 Internship & Work Experience Polish")
                exp_fixes = rep.get("work_experience_improvements", [])
                if isinstance(exp_fixes, list) and exp_fixes:
                    for ef in exp_fixes:
                        if not isinstance(ef, dict):
                            continue
                        comp = ef.get("company_or_role", "Experience")
                        flaw = ef.get("mistake_identified", "")
                        fb = ef.get("from_bullet", "")
                        tb = ef.get("to_bullet", "")
                        tip = ef.get("hiring_tip", "")
                        st.markdown(f"""
                        <div class="diff-card">
                            <h5 style="margin: 0; color: #38bdf8;">🏢 {comp}</h5>
                            <p style="color: #fb7185; font-size: 0.83rem; margin: 0.3rem 0;"><b>⚠️ Area to Improve:</b> {flaw}</p>
                            <span class="text-before">❌ From: "{fb}"</span><br>
                            <span class="text-after">✅ To: "{tb}"</span>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.4rem; margin-bottom: 0;"><b>🎯 Recruiter Tip:</b> {tip}</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("#### 📜 Targeted Certifications")
                certs_data = rep.get("certifications", {})
                if not isinstance(certs_data, dict):
                    certs_data = {}
                free_certs = certs_data.get("free_certifications", [])
                paid_cert = certs_data.get("paid_certification", {})

                c_col1, c_col2 = st.columns([1, 1], gap="medium")
                with c_col1:
                    st.markdown("##### 🟢 2 Recommended Free Certifications")
                    if isinstance(free_certs, list) and free_certs:
                        for fc in free_certs[:2]:
                            if not isinstance(fc, dict):
                                continue
                            fc_title = fc.get("title", "Free Certification")
                            fc_url = fc.get("url", "#")
                            fc_desc = fc.get("desc", "")
                            st.markdown(f"""
                            <div class="diff-card">
                                <span class="badge badge-free">FREE</span> <b><a href="{fc_url}" target="_blank" style="text-decoration: none; color: inherit;">{fc_title}</a></b>
                                <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.3rem; margin-bottom: 0;">{fc_desc}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.write("No specific free certifications identified.")

                with c_col2:
                    st.markdown("##### 🟡 1 Recommended Paid / Industry Credential")
                    if isinstance(paid_cert, dict) and paid_cert:
                        p_title = paid_cert.get("title", "Industry Certification")
                        p_cost = paid_cert.get("cost", "Paid")
                        p_desc = paid_cert.get("desc", "")
                        st.markdown(f"""
                        <div class="diff-card">
                            <span class="badge badge-paid">{p_cost}</span> <b>{p_title}</b>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.3rem; margin-bottom: 0;">{p_desc}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.write("No specific paid credential required.")