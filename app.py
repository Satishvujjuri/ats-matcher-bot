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
# Page Configuration & UI Theme Injection
# ---------------------------------------------------------
st.set_page_config(
    page_title="MatchPro ATS — Recruiter Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom SaaS-style Dark Theme CSS
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #0d1117;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hero Header */
    .hero-container {
        padding: 1.8rem 2rem;
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 14px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero-subtitle {
        color: #8b949e;
        font-size: 1rem;
        margin-top: 0.4rem;
        margin-bottom: 0;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f0f6fc;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.2rem;
    }

    /* Skill Badges */
    .badge {
        display: inline-block;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .badge-matched {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .badge-partial {
        background-color: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .badge-missing {
        background-color: rgba(244, 63, 94, 0.15);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.3);
    }

    /* Expander Container */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Primary Run Button */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: #ffffff;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #1d4ed8, #2563eb);
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }
</style>
""", unsafe_allow_html=True)

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
    candidate_models = ["gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-3-flash"]
    last_exception = None

    for model_name in candidate_models:
        for attempt in range(3):
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
                last_exception = e
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                continue

    raise RuntimeError(f"All model endpoints are busy. Last error: {last_exception}")

# ---------------------------------------------------------
# UI Header
# ---------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">⚡ MatchPro ATS Intelligence Engine</h1>
    <p class="hero-subtitle">Batch Candidate Benchmarking • Core CS Gap Analysis • Production Fit Roadmaps</p>
</div>
""", unsafe_allow_html=True)

if "ats_results" not in st.session_state:
    st.session_state.ats_results = None

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 1. Target Job Description")
    jd_input = st.text_area(
        label="JD Input",
        label_visibility="collapsed",
        height=280,
        placeholder="Paste full job requirements, mandatory languages, frameworks, minimum experience, and core computer science fundamentals..."
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
    analyze_btn = st.button("🚀 Run Comparative Benchmark", use_container_width=True)
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

    with st.spinner("⚡ Parsing resumes and running comparative intelligence analysis..."):
        payload = ""
        skipped_files = []

        for file in uploaded_files:
            file_bytes = file.read()
            extracted_text, is_valid = extract_text(file_bytes, file.name)
            
            if not is_valid:
                skipped_files.append(file.name)
                continue
            
            payload += f"\n--- CANDIDATE: {file.name} ---\n{extracted_text[:10000]}\n"

        if skipped_files:
            st.error(f"⚠️ Unreadable/scanned documents detected: {', '.join(skipped_files)}.")

        if not payload.strip():
            st.stop()

        prompt = f"""
You are an expert ATS recruitment evaluator.
Analyze each candidate strictly against the Job Description.

JOB DESCRIPTION:
{jd_input}

RESUMES:
{payload}

Return ONLY valid JSON matching this schema:
{{
  "candidates": [
    {{
      "name": "Candidate Name or Filename",
      "score": 51
    }}
  ],
  "reports": [
    {{
      "name": "Candidate Name",
      "score": 51,
      "score_category": "Weak Match",
      "score_breakdown": {{
        "skills": "13.1 / 40.0",
        "experience": "20.0 / 25.0",
        "projects": "5.0 / 15.0",
        "education": "10.0 / 10.0",
        "keywords": "2.5 / 10.0"
      }},
      "skills": {{
        "matched": ["Python", "Git", "SQL"],
        "partial": ["PostgreSQL"],
        "missing": ["REST APIs", "CI/CD", "Docker", "AWS", "FastAPI"]
      }},
      "experience_match": "Required: 5+ years | Candidate: 4.0 years | Status: PARTIALLY_MATCHED",
      "education_match": "Required: Bachelor's in CS | Candidate: B.Tech in CS | Status: Matched",
      "gaps": [
        "REST APIs (HIGH PRIORITY): Mandatory requirement needed for backend APIs.",
        "Docker & CI/CD (HIGH PRIORITY): Essential for deployments and automated testing.",
        "AWS (MEDIUM PRIORITY): Cloud hosting experience required."
      ],
      "course_suggestions": [
        {{"title": "FastAPI & REST APIs Mastery", "url": "[https://www.udemy.com/topic/fastapi/](https://www.udemy.com/topic/fastapi/)", "desc": "Bridge Python fundamentals into production-ready API design."}},
        {{"title": "Docker & Kubernetes: The Complete Guide", "url": "[https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/](https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/)", "desc": "Master image builds and CI/CD pipelines."}},
        {{"title": "AWS Cloud Technical Essentials", "url": "[https://www.coursera.org/learn/aws-cloud-technical-essentials](https://www.coursera.org/learn/aws-cloud-technical-essentials)", "desc": "Hands-on mastery of EC2, S3, and cloud infrastructure."}}
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
# Analytics & Candidate Presentation Layer
# ---------------------------------------------------------
if st.session_state.ats_results:
    results = st.session_state.ats_results
    candidates = results.get("candidates", [])
    reports = results.get("reports", [])

    st.markdown("---")
    
    # KPI Metric Cards
    if candidates:
        top_candidate = max(candidates, key=lambda x: x.get("score", 0))
        avg_score = round(sum(c.get("score", 0) for c in candidates) / len(candidates), 1)
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(candidates)}</div>
                <div class="metric-label">Candidates Evaluated</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #38bdf8;">{top_candidate.get('name', 'N/A')[:14]}</div>
                <div class="metric-label">Top Profile</div>
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
                <div class="metric-label">Average Match</div>
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
        fig.update_traces(
            texttemplate='<b>%{text}%</b>',
            textposition='outside',
            marker=dict(line=dict(width=0))
        )
        fig.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
            font=dict(color="#c9d1d9"),
            height=280 + (len(candidates) * 45),
            margin=dict(l=20, r=40, t=20, b=20),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="#21262d"),
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

    # Detailed Candidate Reports with Pill Badges
    st.markdown("### 📋 Candidate Evaluation Drill-Down")

    for rep in reports:
        name = rep.get("name", "Candidate")
        score = rep.get("score", 0)
        badge_style = "badge-matched" if score >= 75 else "badge-partial" if score >= 50 else "badge-missing"
        badge_label = "Strong Match" if score >= 75 else "Moderate Match" if score >= 50 else "Weak Match"

        with st.expander(f"👤 {name} — Score: {score}%", expanded=True):
            r_col1, r_col2 = st.columns([1, 1], gap="medium")

            with r_col1:
                st.markdown(f"**Fit Status:** <span class='badge {badge_style}'>{badge_label} ({score}%)</span>", unsafe_allow_html=True)
                
                st.markdown("<br>**📈 Weighted Score Breakdown:**", unsafe_allow_html=True)
                sb = rep.get("score_breakdown", {})
                for k, v in sb.items():
                    st.write(f"• **{k.title()}**: `{v}`")

                st.markdown("**🎯 Skill Alignments:**")
                skills = rep.get("skills", {})
                
                matched_html = "".join([f"<span class='badge badge-matched'>{s}</span>" for s in skills.get('matched', [])]) or "<i>None</i>"
                partial_html = "".join([f"<span class='badge badge-partial'>{s}</span>" for s in skills.get('partial', [])]) or "<i>None</i>"
                missing_html = "".join([f"<span class='badge badge-missing'>{s}</span>" for s in skills.get('missing', [])]) or "<i>None</i>"

                st.markdown(f"**Matched:**<br>{matched_html}", unsafe_allow_html=True)
                st.markdown(f"**Partial:**<br>{partial_html}", unsafe_allow_html=True)
                st.markdown(f"**Missing:**<br>{missing_html}", unsafe_allow_html=True)

            with r_col2:
                st.markdown("**⏳ Experience Alignment:**")
                st.info(rep.get('experience_match', 'N/A'))

                st.markdown("**🎓 Education Fit:**")
                st.info(rep.get('education_match', 'N/A'))

                st.markdown("**⚠️ Identified Gaps:**")
                for gap in rep.get("gaps", []):
                    st.markdown(f"- {gap}")

                st.markdown("**🚀 Curated Upskilling Roadmaps:**")
                courses = rep.get("course_suggestions", [])
                for c in courses:
                    title = c.get("title", "Course")
                    url = c.get("url", "https://coursera.org")
                    desc = c.get("desc", "")
                    st.markdown(f"📚 **[{title}]({url})** — *{desc}*")