import os
import json
import streamlit as st
import PyPDF2
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

# 1. Page Configuration
st.set_page_config(
    page_title="MatchPro ATS — Recruiter Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# 2. Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-container {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(34, 197, 94, 0.05) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
    }
    
    .winner-banner {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(56, 189, 248, 0.12) 100%);
        border: 1px solid rgba(34, 197, 94, 0.4);
        border-radius: 14px;
        padding: 20px 24px;
        margin: 20px 0;
    }

    .candidate-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 16px;
    }

    .pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 2px;
    }
    .pill-green {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .pill-red {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .pill-amber {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    div.stButton > button {
        background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        opacity: 0.92;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar
api_key = os.environ.get("GEMINI_API_KEY")
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    if not api_key:
        api_key = st.text_input("Gemini API Key:", type="password", placeholder="AIzaSy...")
    else:
        st.success("API Key Active")
    
    st.markdown("---")
    st.markdown("### 🎯 Criteria Inspected")
    st.markdown("""
    - **Skill & Framework Match**
    - **Missing Tech Stacks & Tools**
    - **Missing Core CS Fundamentals**
    - **Targeted Action Steps**
    - **Recommended Upskilling Courses (Min. 3 Links)**
    """)
    st.markdown("---")
    if st.button("🧹 Reset Workspace", use_container_width=True):
        st.session_state.eval_results = None
        st.session_state.chat_history = []
        st.rerun()

# 4. Helper Functions
def extract_pdf_text(file):
    pdf = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()

def analyze_all_resumes(jd_text, resume_dict, client):
    resumes_payload = ""
    for name, content in resume_dict.items():
        resumes_payload += f"\n--- CANDIDATE FILE: {name} ---\n{content}\n"

    prompt = f"""
You are an expert technical ATS evaluator and recruitment specialist.
Assess each candidate's resume strictly against the Job Description.

TARGET JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUMES:
{resumes_payload}

CRITICAL INSTRUCTIONS:
1. Determine match scores (0-100), identify matched skills, missing stacks, and missing CS fundamentals.
2. For EVERY candidate, provide AT LEAST 3 highly relevant, high-quality course recommendations to bridge their missing skills. Include real platform names (e.g. Coursera, Udemy, edX, freeCodeCamp, Harvard CS50) and valid search or course URLs.

Return ONLY valid JSON with this exact structure:
{{
  "top_candidate_label": "Candidate Name or Filename",
  "winner_announcement": "2-3 concise sentences detailing why this profile is the best fit.",
  "candidates": [
    {{
      "display_name": "Candidate Name or File Label",
      "filename": "Filename.pdf",
      "ats_score": 88,
      "match_verdict": "High Match",
      "matched_skills": ["Python", "FastAPI"],
      "missing_languages_tools": ["Docker", "Kubernetes"],
      "missing_stacks_domains": ["AWS Cloud"],
      "missing_core_subjects": ["Operating Systems"],
      "how_to_get_shortlisted": [
        "Quantify project achievements with production metrics",
        "Add a dedicated core CS fundamentals section"
      ],
      "recommended_courses": [
        {{
          "title": "Docker and Kubernetes: The Complete Guide",
          "platform": "Udemy",
          "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/"
        }},
        {{
          "title": "AWS Certified Solutions Architect",
          "platform": "Coursera",
          "url": "https://www.coursera.org/learn/aws-cloud-technical-essentials"
        }},
        {{
          "title": "CS50: Introduction to Computer Science",
          "platform": "edX",
          "url": "https://www.edx.org/cs50"
        }}
      ]
    }}
  ]
}}
"""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return response.text

# 5. Header Area
st.markdown("""
<div class="hero-container">
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 2rem;">⚡</span>
        <div>
            <h2 style="margin: 0; font-weight: 800; letter-spacing: -0.5px;">MatchPro ATS</h2>
            <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">Multi-Candidate Ranking, Skill Gap Matrix & Course Upskilling Engine</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Workbench Input Grid
col_jd, col_res = st.columns([1, 1], gap="medium")

with col_jd:
    st.markdown("#### 1. Target Job Description")
    jd_input = st.text_area(
        "Job Description Input",
        height=210,
        placeholder="Paste job description, requirements, tech stack (Python, React, PostgreSQL)...",
        label_visibility="collapsed"
    )

with col_res:
    st.markdown("#### 2. Candidate Resumes (1 to 3 files)")
    uploaded_files = st.file_uploader(
        "Upload Resumes",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded_files:
        st.info(f"📂 **{len(uploaded_files)} candidate resume(s)** uploaded.")

if "eval_results" not in st.session_state:
    st.session_state.eval_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "full_context" not in st.session_state:
    st.session_state.full_context = ""

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 Evaluate & Benchmark Candidates", use_container_width=True):
    if not api_key:
        st.error("Please provide your Gemini API Key in the sidebar or `.env` file.")
    elif not jd_input.strip():
        st.error("Please paste a Job Description.")
    elif not uploaded_files:
        st.error("Please upload at least 1 resume file.")
    else:
        with st.spinner("Scoring profiles, finding missing competencies & retrieving course recommendations..."):
            try:
                client = genai.Client(api_key=api_key)
                resumes_dict = {}
                for idx, f in enumerate(uploaded_files, start=1):
                    display_key = f"Candidate {idx} ({f.name})"
                    if f.name.endswith(".pdf"):
                        resumes_dict[display_key] = extract_pdf_text(f)
                    else:
                        resumes_dict[display_key] = f.read().decode("utf-8", errors="ignore")

                raw_json = analyze_all_resumes(jd_input, resumes_dict, client)
                data = json.loads(raw_json)
                st.session_state.eval_results = data
                st.session_state.full_context = f"JD:\n{jd_input}\n\nComparative Analysis:\n{raw_json}"
                st.session_state.chat_history = [{
                    "role": "assistant",
                    "content": f"Evaluation complete! **{data.get('top_candidate_label', 'Top Match')}** scored highest. Ask me how any candidate can bridge their gaps."
                }]
            except errors.ClientError as e:
                if "429" in str(e):
                    st.error("⚠️ Quota limit reached on free tier. Please wait 30 seconds and retry.")
                else:
                    st.error(f"Gemini API Error: {str(e)}")
            except Exception as e:
                st.error(f"Error parsing analysis: {str(e)}")

# 7. Results Presentation
if st.session_state.eval_results:
    data = st.session_state.eval_results
    candidates = sorted(data.get("candidates", []), key=lambda x: x.get("ats_score", 0), reverse=True)
    winner = candidates[0] if candidates else {}

    st.markdown("---")

    # Winner Banner
    st.markdown(f"""
    <div class="winner-banner">
        <h3 style="margin: 0; color: #4ade80;">🏆 Top Match: {winner.get('display_name', 'Leading Profile')}</h3>
        <p style="font-size: 1.05rem; margin: 8px 0; color: #f8fafc;">
            <strong>ATS Fit Score:</strong> <code style="color: #38bdf8; font-size: 1.1rem;">{winner.get('ats_score')}%</code> &nbsp;|&nbsp; 
            <strong>Strength:</strong> {winner.get('match_verdict')}
        </p>
        <p style="margin-top: 8px; color: #cbd5e1; line-height: 1.5; font-size: 0.95rem;">{data.get('winner_announcement', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Comparison Grid
    col_chart, col_stat = st.columns([1.3, 0.7], gap="medium")

    with col_chart:
        df_chart = pd.DataFrame([
            {"Candidate": c.get("display_name", c.get("filename")), "ATS Score": c.get("ats_score", 0)}
            for c in candidates
        ])

        fig = px.bar(
            df_chart,
            x="Candidate",
            y="ATS Score",
            text="ATS Score",
            color="ATS Score",
            color_continuous_scale=["#38bdf8", "#0284c7", "#22c55e"],
            range_y=[0, 100],
            title="ATS Match Benchmark (%)"
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0)
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#94a3b8"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            showlegend=False,
            height=300,
            margin=dict(l=10, r=10, t=35, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_stat:
        st.markdown("#### Score Summary")
        for c in candidates:
            score = c.get('ats_score', 0)
            score_color = "#4ade80" if score >= 75 else "#fbbf24"
            st.markdown(f"""
            <div class="candidate-card">
                <div style="font-weight: 600; font-size: 0.9rem; color: #f8fafc;">{c.get('display_name')}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                    <span style="color: #94a3b8; font-size: 0.8rem;">Verdict: {c.get('match_verdict')}</span>
                    <span style="font-size: 1.1rem; font-weight: 700; color: {score_color};">{score}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # In-Depth Gap Analysis & Course Links
    st.markdown("---")
    st.markdown("### 🔍 In-Depth Skill Matrices & Recommended Courses")

    for idx, c in enumerate(candidates, start=1):
        is_top = (idx == 1)
        tag = "⭐ [TOP MATCH]" if is_top else ""
        with st.expander(f"📄 {c.get('display_name')} — Score: {c.get('ats_score')}% {tag}", expanded=is_top):
            col_l, col_r = st.columns(2, gap="large")

            with col_l:
                st.markdown("**✅ Matched Tech & Keywords**")
                matched = c.get("matched_skills", [])
                if matched:
                    st.markdown(" ".join([f"<span class='pill pill-green'>{s}</span>" for s in matched]), unsafe_allow_html=True)
                else:
                    st.caption("No direct keywords matched.")

                st.markdown("<br>**❌ Missing Tools & Stacks**", unsafe_allow_html=True)
                missing = c.get("missing_languages_tools", []) + c.get("missing_stacks_domains", [])
                if missing:
                    st.markdown(" ".join([f"<span class='pill pill-red'>{s}</span>" for s in missing]), unsafe_allow_html=True)
                else:
                    st.caption("None missing.")

                st.markdown("<br>**📚 Missing Core Subjects**", unsafe_allow_html=True)
                core = c.get("missing_core_subjects", [])
                if core:
                    st.markdown(" ".join([f"<span class='pill pill-amber'>{s}</span>" for s in core]), unsafe_allow_html=True)
                else:
                    st.caption("None missing.")

            with col_r:
                st.markdown("**🎯 Roadmap to Get Shortlisted**")
                for step in c.get("how_to_get_shortlisted", []):
                    st.markdown(f"- {step}")

                st.markdown("<br>**🎓 Recommended Upskilling Courses (Minimum 3)**", unsafe_allow_html=True)
                courses = c.get("recommended_courses", [])
                if courses:
                    for course in courses:
                        c_title = course.get("title", "Online Certification Course")
                        c_platform = course.get("platform", "Platform")
                        c_url = course.get("url", "https://www.coursera.org")
                        st.markdown(f"- 🔗 [{c_title} ({c_platform})]({c_url})")
                else:
                    st.markdown("- 🔗 [CS50: Introduction to Computer Science (edX)](https://www.edx.org/cs50)")
                    st.markdown("- 🔗 [Full Stack Open (University of Helsinki)](https://fullstackopen.com/en/)")
                    st.markdown("- 🔗 [Python and Django Full Stack Bootcamp (Udemy)](https://www.udemy.com)")

    # Recruiter Chat
    st.markdown("---")
    st.markdown("### 💬 Recruiter Gap Assistant")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input("Ask how Candidate 2 can improve their score or what courses they should take..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing profile gaps..."):
                try:
                    client = genai.Client(api_key=api_key)
                    chat_res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=f"Context:\n{st.session_state.full_context}\n\nUser Question: {query}\nProvide direct, actionable recruiter feedback with course links if relevant."
                    )
                    reply = chat_res.text
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except errors.ClientError as e:
                    if "429" in str(e):
                        err_msg = "⚠️ Quota limit reached. Please wait ~30 seconds before sending another question."
                    else:
                        err_msg = f"Chat error: {e}"
                    st.warning(err_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": err_msg})