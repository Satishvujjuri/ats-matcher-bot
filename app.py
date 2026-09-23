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
# Dual Theme Dynamic Styling Engine (Streamlit Native Overrides)
# ---------------------------------------------------------
if st.session_state.theme_mode == "Dark":
    theme_css = """
    <style>
        .stApp { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        /* Hero Container */
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
        .hero-subtitle { color: #8b949e; font-size: 0.95rem; margin-top: 0.3rem; }

        /* Metric & Diff Cards */
        .metric-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 1.1rem;
            text-align: center;
        }
        .metric-value { font-size: 1.7rem; font-weight: 700; color: #f0f6fc; }
        .metric-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .diff-card {
            background-color: #161b22;
            border: 1px solid #2d333b;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.8rem;
        }
        .text-before { color: #fb7185; font-size: 0.88rem; font-family: monospace; }
        .text-after { color: #4ade80; font-size: 0.88rem; font-family: monospace; font-weight: 600; }

        /* Badges */
        .badge { display: inline-block; padding: 0.22rem 0.65rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; margin: 0.2rem; }
        .badge-matched { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-partial { background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-missing { background-color: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-free { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-paid { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

        /* Streamlit Native Inputs (Dark Mode) */
        textarea, .stTextArea textarea {
            background-color: #161b22 !important;
            color: #f0f6fc !important;
            border: 1px solid #30363d !important;
            border-radius: 8px !important;
        }
        [data-testid="stFileUploader"] {
            background-color: #161b22 !important;
            border: 1px dashed #30363d !important;
            border-radius: 8px !important;
            padding: 0.8rem !important;
        }
        [data-testid="stFileUploader"] * {
            color: #c9d1d9 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #161b22 !important;
            color: #f0f6fc !important;
            border-color: #30363d !important;
        }
    </style>
    """
else:
    theme_css = """
    <style>
        .stApp { background-color: #f8fafc; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        /* Hero Container */
        .hero-container {
            padding: 1.8rem 2rem;
            background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }
        .hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            background: linear-gradient(90deg, #0284c7, #4f46e5, #9333ea);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .hero-subtitle { color: #475569; font-size: 0.95rem; margin-top: 0.3rem; font-weight: 500; }

        /* Headers & Labels */
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
            color: #0f172a !important;
        }

        /* Metric & Diff Cards */
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 1.1rem;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }
        .metric-value { font-size: 1.7rem; font-weight: 700; color: #0f172a; }
        .metric-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }

        .diff-card {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
        .text-before { color: #be123c; font-size: 0.88rem; font-family: monospace; font-weight: 600; }
        .text-after { color: #15803d; font-size: 0.88rem; font-family: monospace; font-weight: 600; }

        /* Badges */
        .badge { display: inline-block; padding: 0.22rem 0.65rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; margin: 0.2rem; }
        .badge-matched { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-partial { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-missing { background-color: #ffe4e6; color: #be123c; border: 1px solid #fca5a5; }
        .badge-free { background-color: #ecfdf5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-paid { background-color: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }

        /* Streamlit Native Inputs (Light Mode Overrides) */
        textarea, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.04) !important;
        }
        textarea::placeholder {
            color: #94a3b8 !important;
        }

        /* File Uploader Container & Dropzone */
        [data-testid="stFileUploader"] {
            background-color: #ffffff !important;
            border: 2px dashed #cbd5e1 !important;
            border-radius: 10px !important;
            padding: 1rem !important;
        }
        [data-testid="stFileUploader"] section {
            background-color: #f8fafc !important;
            border-radius: 8px !important;
        }
        [data-testid="stFileUploader"] * {
            color: #1e293b !important;
        }
        [data-testid="stFileUploader"] button {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }

        /* Selectbox (Theme dropdown) */
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        div[data-baseweb="select"] * {
            color: #0f172a !important;
        }

        /* Expanders & Tabs */
        .streamlit-expanderHeader {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }
        button[data-baseweb="tab"] {
            color: #475569 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #0284c7 !important;
            border-bottom-color: #0284c7 !important;
        }

        /* Run Button */
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
# Resilient API Call Engine
# ---------------------------------------------------------
def clean_json_string(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()

def generate_with_resilience(prompt: str) -> str:
    # Use only confirmed, active models for your API key
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
                # Exponential backoff with jitter to recover from rate limits
                sleep_time = (2 ** attempt) + random.uniform(1.0, 2.5)
                time.sleep(sleep_time)

    # If all attempts fail, show the exact reason from each attempt
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
        <p class="hero-subtitle">Multi-Resume Benchmarking • Precise From-To Phrasing Audits • Production Project Upgrades</p>
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

    with st.spinner("⚡ Running deep evaluation: ATS Matching, Precise Phrasing Diff, and Project Engineering Overhaul..."):
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
You are an elite ATS recruitment architect and principal software engineering hiring director.
Analyze each candidate strictly against the Job Description AND conduct a granular resume transformation audit.

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
        "Distributed message streaming (Kafka) is missing from production background.",
        "No in-memory caching (Redis) mentioned in backend workflows."
      ],
      "link_and_contact_audit": {{
        "current_placement": "LinkedIn and GitHub are pasted as raw URLs at the bottom of page 1.",
        "recommended_placement": "Move hyperlinked handles ('[github.com/username](https://github.com/username)', '[linkedin.com/in/username](https://linkedin.com/in/username)') into the top header directly under name and contact info.",
        "reasoning": "ATS parsers parse the top 100 words for candidate contact profiles; links at the bottom get ignored or misclassified."
      }},
      "phrasing_and_grammar_fixes": [
        {{
          "category": "Spelling / Typo",
          "from_text": "Experienced in building RESTfull web apis using Postgress.",
          "to_text": "Experienced in engineering RESTful web APIs using PostgreSQL.",
          "reasoning": "Eliminates typos on industry-standard technical keywords that cause ATS keyword filter drops."
        }},
        {{
          "category": "Passive to Impact Verbs",
          "from_text": "Was responsible for handling database queries and bugs.",
          "to_text": "Optimized complex SQL queries and resolved critical backend bugs, reducing query response times by 28%.",
          "reasoning": "Replaces passive duty phrasing with active leadership and quantifiable performance impact."
        }}
      ],
      "role_upgrade_suggestions": [
        {{
          "current_title": "Software Developer Intern",
          "recommended_title": "Junior Backend & Cloud Engineer",
          "reasoning": "Aligns your resume headline closer to the target backend/cloud requirements in this JD."
        }}
      ],
      "project_deep_dive": [
        {{
          "project_name": "E-Commerce Web Platform",
          "current_summary": "Built a shop website where users can purchase items with authentication and payment.",
          "identified_mistakes": [
            "Lacks mentions of architecture scalability, concurrency handling, or database schema design.",
            "No metrics indicating test coverage or deployment pipelines."
          ],
          "from_bullet": "Made backend endpoints and connected database.",
          "to_bullet": "Engineered 14+ secure REST endpoints using FastAPI and PostgreSQL with JWT authentication and Stripe webhook integration.",
          "upgrade_roadmap": [
            "Upgrade 1: Introduce Redis caching to store frequently retrieved product catalogs.",
            "Upgrade 2: Containerize services with Docker Compose and set up a GitHub Actions CI/CD pipeline."
          ]
        }}
      ],
      "certifications": {{
        "free_certifications": [
          {{"title": "freeCodeCamp Back End Development & APIs", "url": "[https://www.freecodecamp.org/learn/back-end-development-and-apis/](https://www.freecodecamp.org/learn/back-end-development-and-apis/)", "desc": "Free foundational cert covering Node.js, Express, MongoDB, and microservices."}},
          {{"title": "CS50's Introduction to Computer Science (Harvard/edX)", "url": "[https://www.edx.org/cs50](https://www.edx.org/cs50)", "desc": "Free audit path covering memory management, data structures, and algorithms."}}
        ],
        "paid_certifications": [
          {{"title": "AWS Certified Solutions Architect – Associate (SAA-C03)", "provider": "Amazon Web Services", "cost": "~$150 USD", "desc": "Gold standard for cloud infrastructure, networking, and microservices architecture."}},
          {{"title": "Certified Kubernetes Application Developer (CKAD)", "provider": "Linux Foundation", "cost": "~$395 USD", "desc": "Top-tier container orchestration credential proving deployment skills."}}
        ]
      }},
      "course_suggestions": [
        {{"title": "Apache Kafka for Beginners", "url": "[https://www.udemy.com/course/apache-kafka/](https://www.udemy.com/course/apache-kafka/)", "desc": "Master distributed event streaming and message brokers."}},
        {{"title": "AWS Cloud Technical Essentials", "url": "[https://www.coursera.org/learn/aws-cloud-technical-essentials](https://www.coursera.org/learn/aws-cloud-technical-essentials)", "desc": "Hands-on mastery of ECS, EC2, and S3."}}
      ]
    }}
  ]
}}
"""
        try:
            raw_response = generate_with_resilience(prompt)
            clean_json = clean_json_string(raw_response)
            data = json.loads(clean_json)
            st.session_state.ats_results = {
                "candidates": data.get("candidates", []),
                "reports": data.get("reports", [])
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
    
    # Summary KPI Cards
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
                <div class="metric-value" style="color: #38bdf8;">{top_candidate.get('name', 'N/A')[:14]}</div>
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

        # Plotly Benchmark Chart
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
        font_col = "#c9d1d9" if st.session_state.theme_mode == "Dark" else "#1e293b"
        grid_col = "#21262d" if st.session_state.theme_mode == "Dark" else "#e2e8f0"

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

        # Export CSV Button
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Benchmark to CSV",
            data=csv_data,
            file_name="ats_benchmark_report.csv",
            mime="text/csv"
        )

    # Detailed Candidate Reports with 3 Upgraded Tabs
    st.markdown("### 📋 Candidate Evaluation Drill-Down")

    for rep in reports:
        name = rep.get("name", "Candidate")
        score = rep.get("score", 0)
        badge_style = "badge-matched" if score >= 75 else "badge-partial" if score >= 50 else "badge-missing"
        badge_label = "Strong Match" if score >= 75 else "Moderate Match" if score >= 50 else "Weak Match"

        with st.expander(f"👤 {name} — Score: {score}% ({badge_label})", expanded=True):
            tab1, tab2, tab3 = st.tabs(["🎯 1. ATS Fit & Skill Gaps", "🔍 2. Resume Hygiene & From➔To Audits", "🚀 3. Projects Overhaul & Certifications"])

            # TAB 1: ATS Scoring & Skills
            with tab1:
                t1_col1, t1_col2 = st.columns([1, 1], gap="medium")
                with t1_col1:
                    st.markdown(f"**Fit Status:** <span class='badge {badge_style}'>{badge_label} ({score}%)</span>", unsafe_allow_html=True)
                    st.markdown("<br>**📈 Weighted Score Breakdown:**", unsafe_allow_html=True)
                    sb = rep.get("score_breakdown", {})
                    for k, v in sb.items():
                        st.write(f"• **{k.title()}**: `{v}`")

                    st.markdown("**🎯 Technical Skill Alignment:**")
                    skills = rep.get("skills", {})
                    matched_html = "".join([f"<span class='badge badge-matched'>{s}</span>" for s in skills.get('matched', [])]) or "<i>None</i>"
                    partial_html = "".join([f"<span class='badge badge-partial'>{s}</span>" for s in skills.get('partial', [])]) or "<i>None</i>"
                    missing_html = "".join([f"<span class='badge badge-missing'>{s}</span>" for s in skills.get('missing', [])]) or "<i>None</i>"

                    st.markdown(f"**Matched:**<br>{matched_html}", unsafe_allow_html=True)
                    st.markdown(f"**Partial:**<br>{partial_html}", unsafe_allow_html=True)
                    st.markdown(f"**Missing:**<br>{missing_html}", unsafe_allow_html=True)

                with t1_col2:
                    st.markdown("**⏳ Experience Alignment:**")
                    st.info(rep.get('experience_match', 'N/A'))

                    st.markdown("**🎓 Education Fit:**")
                    st.info(rep.get('education_match', 'N/A'))

                    st.markdown("**⚠️ Identified Gaps:**")
                    for gap in rep.get("gaps", []):
                        st.markdown(f"- {gap}")

            # TAB 2: Resume Hygiene, Links & Precise From➔To Fixes
            with tab2:
                st.markdown("#### 🔗 Hyperlinks & Profile Placement Audit")
                link_audit = rep.get("link_and_contact_audit", {})
                st.markdown(f"""
                <div class="diff-card">
                    <span style="font-weight: 700; color: #fb7185;">❌ Current Placement:</span><br>
                    <span class="text-before">{link_audit.get('current_placement', 'N/A')}</span><br><br>
                    <span style="font-weight: 700; color: #4ade80;">✅ Recommended Placement:</span><br>
                    <span class="text-after">{link_audit.get('recommended_placement', 'N/A')}</span>
                    <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.5rem; margin-bottom: 0;"><b>Why this matters:</b> {link_audit.get('reasoning', '')}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### ✍️ Granular 'From ➔ To' Phrasing & Grammar Transformations")
                fixes = rep.get("phrasing_and_grammar_fixes", [])
                if fixes:
                    for f in fixes:
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
                if roles:
                    for r in roles:
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

            # TAB 3: Projects Deep-Dive & Free/Paid Certifications
            with tab3:
                st.markdown("#### 🛠️ Project Architecture Analysis & Upgrade Roadmaps")
                projects = rep.get("project_deep_dive", [])
                if projects:
                    for proj in projects:
                        p_name = proj.get("project_name", "Project")
                        summary = proj.get("current_summary", "")
                        mistakes = proj.get("identified_mistakes", [])
                        from_b = proj.get("from_bullet", "")
                        to_b = proj.get("to_bullet", "")
                        roadmaps = proj.get("upgrade_roadmap", [])

                        with st.container():
                            st.markdown(f"""
                            <div class="diff-card">
                                <h4 style="margin: 0; color: #38bdf8;">📌 {p_name}</h4>
                                <p style="color: #8b949e; font-size: 0.88rem; margin-top: 0.3rem;"><i>{summary}</i></p>
                                
                                <b style="color: #fb7185; font-size: 0.88rem;">⚠️ Identified Flaws & Blindspots:</b>
                                <ul style="color: #8b949e; font-size: 0.85rem; margin-top: 0.2rem; margin-bottom: 0.6rem;">
                                    {"".join([f"<li>{m}</li>" for m in mistakes])}
                                </ul>

                                <b style="font-size: 0.88rem;">Impact Bullet Rewrite:</b><br>
                                <span class="text-before">❌ From: "{from_b}"</span><br>
                                <span class="text-after">✅ To: "{to_b}"</span><br><br>

                                <b style="color: #38bdf8; font-size: 0.88rem;">🚀 Architectural Upgrade Roadmap:</b>
                                <ul style="color: #4ade80; font-size: 0.85rem; margin-top: 0.2rem; margin-bottom: 0;">
                                    {"".join([f"<li>{r}</li>" for r in roadmaps])}
                                </ul>
                            </div>
                            """, unsafe_allow_html=True)

                st.markdown("#### 📜 Targeted Certifications (Free vs. Industry Paid)")
                certs_data = rep.get("certifications", {})
                free_certs = certs_data.get("free_certifications", [])
                paid_certs = certs_data.get("paid_certifications", [])

                c_col1, c_col2 = st.columns([1, 1], gap="medium")
                with c_col1:
                    st.markdown("##### 🟢 Free / Open-Access Certifications")
                    for fc in free_certs:
                        title = fc.get("title", "Cert")
                        url = fc.get("url", "#")
                        desc = fc.get("desc", "")
                        st.markdown(f"""
                        <div class="diff-card">
                            <span class="badge badge-free">FREE</span> <b><a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">{title}</a></b>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.3rem; margin-bottom: 0;">{desc}</p>
                        </div>
                        """, unsafe_allow_html=True)

                with c_col2:
                    st.markdown("##### 🟡 High-Value Industry Paid Credentials")
                    for pc in paid_certs:
                        title = pc.get("title", "Cert")
                        provider = pc.get("provider", "")
                        cost = pc.get("cost", "")
                        desc = pc.get("desc", "")
                        st.markdown(f"""
                        <div class="diff-card">
                            <span class="badge badge-paid">{cost}</span> <b>{title}</b> <span style="color: #8b949e; font-size: 0.8rem;">({provider})</span>
                            <p style="color: #8b949e; font-size: 0.83rem; margin-top: 0.3rem; margin-bottom: 0;">{desc}</p>
                        </div>
                        """, unsafe_allow_html=True)