import os
import json
import streamlit as st
import PyPDF2
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

# 1. Streamlit Page Setup
st.set_page_config(
    page_title="MatchPro ATS — Recruiter Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_dotenv()

# 2. Hardcore Pro Glassmorphic UI & Animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Ambient Background Glow */
    .stApp {
        background: radial-gradient(circle at 50% -20%, rgba(14, 165, 233, 0.12) 0%, rgba(10, 15, 29, 0) 50%),
                    radial-gradient(circle at 100% 60%, rgba(168, 85, 247, 0.08) 0%, rgba(10, 15, 29, 0) 40%),
                    #070b14 !important;
        color: #f1f5f9;
    }

    /* Glass Floating Top Navigation */
    .glass-nav {
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px 30px;
        margin-bottom: 30px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Radiant Animated Gradient Header */
    .gradient-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, #ffffff 0%, #38bdf8 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.1;
    }

    .badge-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 9999px;
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #38bdf8;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #38bdf8;
        box-shadow: 0 0 10px #38bdf8;
    }

    /* Section Cards */
    .glass-card {
        background: rgba(15, 23, 42, 0.5);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }

    /* Winner Spotlight Hero */
    .winner-card {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.14) 0%, rgba(56, 189, 248, 0.08) 50%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(34, 197, 94, 0.4);
        border-radius: 18px;
        padding: 24px;
        margin: 24px 0;
        backdrop-filter: blur(16px);
        box-shadow: 0 20px 40px -10px rgba(34, 197, 94, 0.15);
    }

    /* Skill Badges & Tags */
    .pill {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 3px 2px;
    }
    .pill-green {
        background: rgba(34, 197, 94, 0.12);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.28);
    }
    .pill-red {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.28);
    }
    .pill-amber {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.28);
    }

    /* Custom Futuristic Action Button */
    div.stButton > button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 50%, #2563eb 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.02em !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        padding: 14px 28px !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 30px -5px rgba(2, 132, 199, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) scale(1.005) !important;
        box-shadow: 0 15px 35px -5px rgba(2, 132, 199, 0.7), 0 0 20px rgba(56, 189, 248, 0.4) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) scale(0.99) !important;
    }

    /* Inputs Focus Polish */
    .stTextArea textarea {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
    }
    .stTextArea textarea:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar Engine Configuration
api_key = os.environ.get("GEMINI_API_KEY")
with st.sidebar:
    st.markdown("### ⚙️ Engine Matrix")
    if not api_key:
        api_key = st.text_input("Gemini API Key:", type="password", placeholder="AIzaSy...")
    else:
        st.success("API Key Loaded (.env / Secrets)")
    
    st.markdown("---")
    st.markdown("### 🔬 Verification Filters")
    st.markdown("""
    - ⚡ **Weighted Keyword Scoring**
    - 🔍 **Missing Tech Stack (MERN / Cloud)**
    - 📚 **Core CS (OS, DBMS, CN, DSA)**
    - 🎓 **Verified Course Links (Min. 3)**
    - 💬 **Context-Aware Gap Bot**
    """)
    st.markdown("---")
    if st.button("🧹 Reset Workspace", use_container_width=True):
        st.session_state.eval_results = None
        st.session_state.chat_history = []
        st.session_state.full_context = ""
        st.rerun()

# 4. Parsing & Prompt Logic
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
You are an expert technical ATS evaluator and recruitment lead.
Assess each candidate's resume strictly against the Job Description.

TARGET JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUMES:
{resumes_payload}

CRITICAL REQUIREMENTS:
1. Assign an accurate ATS score (0-100), identify matched skills, missing stacks, and missing CS fundamentals.
2. For EVERY candidate, generate AT LEAST 3 highly relevant upskilling course recommendations with valid, direct search/course hyperlinks from platforms like Coursera, Udemy, edX, or Harvard.

Return ONLY valid JSON formatted exactly like this:
{{
  "top_candidate_label": "Candidate Name or Filename",
  "winner_announcement": "2-3 concise sentences detailing why this profile won.",
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
        "Include production metrics on backend API throughput",
        "Add practical DBMS optimization projects"
      ],
      "recommended_courses": [
        {{
          "title": "Docker and Kubernetes: The Complete Guide",
          "platform": "Udemy",
          "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/"
        }},
        {{
          "title": "AWS Cloud Technical Essentials",
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

# 5. Glowing Glass Top Navbar
st.markdown("""
<div class="glass-nav">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="width: 46px; height: 46px; border-radius: 14px; background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);">
            <span style="font-size: 1.5rem;">⚡</span>
        </div>
        <div>
            <h1 class="gradient-title">MatchPro ATS</h1>
            <p style="margin: 0; color: #94a3b8; font-size: 0.88rem; font-weight: 500;">AI-Powered Multi-Resume Benchmark & Gap Intelligence</p>
        </div>
    </div>
    <div class="badge-status">
        <span class="status-dot"></span>
        gemini-3.6-flash Active
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Workbench Input Panels
col_jd, col_res = st.columns([1, 1], gap="large")

with col_jd:
    st.markdown("##### 🎯 1. Target Job Description")
    jd_input = st.text_area(
        "Job Description Input",
        height=220,
        placeholder="Paste JD requirements, tech stacks (e.g. Python, Docker, PostgreSQL, React), and qualifications...",
        label_visibility="collapsed"
    )

with col_res:
    st.markdown("##### 📂 2. Candidate Resumes (1 to 3 files)")
    uploaded_files = st.file_uploader(
        "Upload Resumes",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded_files:
        st.info(f"✨ **{len(uploaded_files)} Candidate Profile(s)** ready for evaluation.")

# Session States
if "eval_results" not in st.session_state:
    st.session_state.eval_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "full_context" not in st.session_state:
    st.session_state.full_context = ""

st.markdown("<br>", unsafe_allow_html=True)

# 7. Action Button
if st.button("🚀 Run Comparative Benchmark & Generate Intelligence Report", use_container_width=True):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar or `.env` file.")
    elif not jd_input.strip():
        st.error("Please provide the Job Description.")
    elif not uploaded_files:
        st.error("Please upload at least 1 resume.")
    else:
        with st.spinner("Scoring profiles, indexing skill matrices, and finding verified course links..."):
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
                    "content": f"Evaluation complete! **{data.get('top_candidate_label', 'Top Candidate')}** has the strongest match. Ask me anything about bridging specific gaps."
                }]
            except errors.ClientError as e:
                if "429" in str(e):
                    st.error("⚠️ Quota limit reached on free tier. Please wait 30 seconds and retry.")
                else:
                    st.error(f"Gemini API Error: {str(e)}")
            except Exception as e:
                st.error(f"Error parsing analysis: {str(e)}")

# 8. Results View
if st.session_state.eval_results:
    data = st.session_state.eval_results
    candidates = sorted(data.get("candidates", []), key=lambda x: x.get("ats_score", 0), reverse=True)
    winner = candidates[0] if candidates else {}

    st.markdown("---")

    # Winner Hero Card
    st.markdown(f"""
    <div class="winner-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h3 style="margin: 0; color: #4ade80; font-size: 1.35rem; font-weight: 700;">🏆 Top Match: {winner.get('display_name', 'Leading Profile')}</h3>
            <span style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.15); padding: 4px 16px; border-radius: 9999px; border: 1px solid rgba(56, 189, 248, 0.3);">
                {winner.get('ats_score')}% ATS Fit
            </span>
        </div>
        <p style="margin-top: 12px; color: #cbd5e1; line-height: 1.6; font-size: 0.95rem;">{data.get('winner_announcement', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Visualization & Metrics Grid
    col_chart, col_stat = st.columns([1.3, 0.7], gap="large")

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
            title="Comparative Candidate Match Benchmark (%)"
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
        st.markdown("##### 📊 Benchmark Summary")
        for c in candidates:
            score = c.get('ats_score', 0)
            score_color = "#4ade80" if score >= 75 else "#fbbf24"
            st.markdown(f"""
            <div class="glass-card" style="margin-bottom: 12px; padding: 14px 18px;">
                <div style="font-weight: 600; font-size: 0.92rem; color: #f8fafc;">{c.get('display_name')}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                    <span style="color: #94a3b8; font-size: 0.8rem;">Verdict: {c.get('match_verdict')}</span>
                    <span style="font-size: 1.15rem; font-weight: 700; color: {score_color};">{score}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Detailed In-Depth Skill Matrices & Verified Links
    st.markdown("---")
    st.markdown("### 🔍 Skill Matrix & Hyperlinked Upskilling Roadmap")

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

                st.markdown("<br>**🎓 Recommended Upskilling Courses (Clickable)**", unsafe_allow_html=True)
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
                    st.markdown("- 🔗 [Python & Backend Masterclass (Udemy)](https://www.udemy.com)")

    # 9. Recruiter Chat Assistant
    st.markdown("---")
    st.markdown("### 💬 Recruiter Gap Assistant")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input("Ask how candidate 2 can beat candidate 1 or what specific courses to take..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing candidate comparison..."):
                try:
                    client = genai.Client(api_key=api_key)
                    chat_res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=f"Context:\n{st.session_state.full_context}\n\nUser Question: {query}\nProvide concise recruiter guidance with clickable links when applicable."
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