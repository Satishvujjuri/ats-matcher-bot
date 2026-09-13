import os
import io
import re
import json
import time
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
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="MatchPro ATS — Recruiter Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Environment & API Key Resolution
# ---------------------------------------------------------
load_dotenv()

try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ `GEMINI_API_KEY` is missing. Add it to Streamlit Cloud Secrets or your local `.env` file.")
    st.stop()

ai_client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------
# Document Extraction Engine (Zero DLL Dependencies)
# ---------------------------------------------------------
def extract_docx_native(file_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            xml_content = docx_zip.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [node.text for node in tree.iterfind('.//w:t', namespaces) if node.text]
            return " ".join(texts)
    except Exception as e:
        st.warning(f"DOCX extraction note: {e}")
        return ""

def extract_text(file_bytes, filename):
    filename = filename.lower()
    text = ""
    try:
        if filename.endswith(".pdf"):
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif filename.endswith(".docx"):
            text = extract_docx_native(file_bytes)
        elif filename.endswith(".doc"):
            raw = file_bytes.decode("latin-1", errors="ignore")
            text_blocks = re.findall(r'[a-zA-Z0-9.,;:!?/@#%&()\-_+=\n ]{4,}', raw)
            text = " ".join([b.strip() for b in text_blocks if len(b.strip()) > 3])
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        st.warning(f"File extraction error for {filename}: {e}")
    return text.strip()

# ---------------------------------------------------------
# Gemini API Fallback Invocation Engine
# ---------------------------------------------------------
# Updated AI Fallback Generator with active Gemini models
def generate_with_fallback(prompt):
    candidate_models = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
    last_err = None
    
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_err = e
                time.sleep((2 ** attempt) + 1)
                continue
    raise RuntimeError(f"All Gemini model calls failed: {last_err}")

# ---------------------------------------------------------
# UI Layout & Application Logic
# ---------------------------------------------------------
st.title("⚡ MatchPro ATS Recruiter Dashboard")
st.caption("AI-Powered Multi-Resume Benchmarking, Core CS Gap Analysis & Upskilling Roadmaps")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1. Target Job Description")
    jd_input = st.text_area(
        "Paste Job Requirements / JD Text:",
        height=260,
        placeholder="Paste full job description, mandatory tech stacks, qualifications, and core CS requirements..."
    )

with col_right:
    st.subheader("2. Candidate Resumes")
    uploaded_files = st.file_uploader(
        "Upload 1 to 5 Resumes (.pdf, .docx, .doc, .txt)",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True
    )
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} candidate resume(s) uploaded.")

analyze_btn = st.button("🚀 Run Comparative Benchmark", type="primary", use_container_width=True)

if analyze_btn:
    if not jd_input.strip():
        st.warning("⚠️ Please provide a target Job Description first.")
        st.stop()
    if not uploaded_files:
        st.warning("⚠️ Please upload at least one candidate resume.")
        st.stop()

    with st.spinner("⚡ Extracting candidate profiles and evaluating contextual fit..."):
        payload = ""
        for file in uploaded_files:
            file_bytes = file.read()
            extracted_text = extract_text(file_bytes, file.name)
            payload += f"\n--- CANDIDATE: {file.name} ---\n{extracted_text[:2500]}\n"

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
        "⚠️ REST APIs (HIGH PRIORITY): Mandatory requirement needed for backend APIs.",
        "⚠️ Docker & CI/CD (HIGH PRIORITY): Essential for deployments and automated testing.",
        "⚠️ AWS (MEDIUM PRIORITY): Cloud hosting experience required."
      ],
      "course_suggestions": [
        {{"title": "FastAPI & REST APIs Mastery", "url": "https://www.udemy.com/topic/fastapi/", "desc": "Bridge Python fundamentals into production-ready API design."}},
        {{"title": "Docker & Kubernetes: The Complete Guide", "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/", "desc": "Master image builds and CI/CD pipelines."}},
        {{"title": "AWS Cloud Technical Essentials", "url": "https://www.coursera.org/learn/aws-cloud-technical-essentials", "desc": "Hands-on mastery of EC2, S3, and cloud infrastructure."}}
      ]
    }}
  ]
}}
"""
        try:
            raw_json = generate_with_fallback(prompt)
            data = json.loads(raw_json)
            candidates_data = data.get("candidates", [])
            reports = data.get("reports", [])

            st.session_state["ats_results"] = {"candidates": candidates_data, "reports": reports}
        except Exception as e:
            st.error(f"Analysis failed: {e}")

# ---------------------------------------------------------
# Benchmark & Visual Analytics Render
# ---------------------------------------------------------
if "ats_results" in st.session_state:
    results = st.session_state["ats_results"]
    candidates = results.get("candidates", [])
    reports = results.get("reports", [])

    st.markdown("---")
    st.subheader("📊 Candidate Comparative Fit Benchmark")

    if candidates:
        df = pd.DataFrame(candidates)
        df = df.sort_values(by="score", ascending=True)

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
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(
            template="plotly_dark",
            height=300 + (len(candidates) * 35),
            margin=dict(l=20, r=20, t=30, b=20),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Detailed Candidate Reports")

    for rep in reports:
        name = rep.get("name", "Candidate")
        score = rep.get("score", 0)
        cat = rep.get("score_category", "Evaluated")
        badge = "🟢 Strong Match" if score >= 75 else "🟡 Moderate Match" if score >= 50 else "🔴 Weak Match"

        with st.expander(f"👤 {name} — {score}% ({badge})", expanded=True):
            r_col1, r_col2 = st.columns([1, 1])

            with r_col1:
                st.markdown("**📈 Score Breakdown:**")
                sb = rep.get("score_breakdown", {})
                for k, v in sb.items():
                    st.write(f"- **{k.title()}**: {v}")

                st.markdown("**🎯 Skill Alignment:**")
                skills = rep.get("skills", {})
                st.write(f"✅ **Matched:** {', '.join(skills.get('matched', [])) or 'None'}")
                st.write(f"⚡ **Partial:** {', '.join(skills.get('partial', [])) or 'None'}")
                st.write(f"❌ **Missing:** {', '.join(skills.get('missing', [])) or 'None'}")

            with r_col2:
                st.markdown("**⏳ Experience & Education Match:**")
                st.write(f"• **Experience:** {rep.get('experience_match', 'N/A')}")
                st.write(f"• **Education:** {rep.get('education_match', 'N/A')}")

                st.markdown("**⚠️ Key Gaps & Discrepancies:**")
                for gap in rep.get("gaps", []):
                    st.write(f"- {gap}")

            st.markdown("**🚀 Recommended Next Steps & Upskilling Courses:**")
            courses = rep.get("course_suggestions", [])
            for c in courses:
                title = c.get("title", "Course")
                url = c.get("url", "https://coursera.org")
                desc = c.get("desc", "")
                st.markdown(f"- 📚 [{title}]({url}) — *{desc}*")