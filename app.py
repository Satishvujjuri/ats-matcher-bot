import os
import json
import streamlit as st
import PyPDF2
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors

# Load .env file automatically
load_dotenv()

st.set_page_config(page_title="Multi-Resume ATS Matcher & Visual Ranker", page_icon="📊", layout="wide")

# API Configuration
api_key = os.environ.get("GEMINI_API_KEY")
with st.sidebar:
    st.title("⚙️ Configuration")
    if not api_key:
        api_key = st.text_input("Gemini API Key:", type="password")
    else:
        st.success("API Key loaded from .env")
    st.markdown("---")
    st.markdown("### Evaluation Scope:")
    st.markdown("- **ATS Score Visual Graph**\n- **Best Candidate Selection**\n- **Missing Languages (Java, Python, C++)**\n- **Missing Stacks (MERN, MEAN)**\n- **Missing Core Subjects (OS, DBMS, Networks)**")

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
You are an expert ATS (Applicant Tracking System) and hiring manager.
Evaluate each candidate resume against the Job Description (JD) below.

### TARGET JOB DESCRIPTION:
{jd_text}

### CANDIDATE RESUMES:
{resumes_payload}

---
### INSTRUCTIONS:
1. Assign an accurate ATS score (0-100) to each candidate based on keyword alignment, stack match, and experience.
2. Compare all candidates and determine the single best candidate.
3. For each candidate, identify:
   - Matched skills
   - Missing languages/tools (e.g., Python, Java, C++, React)
   - Missing domains/stacks (e.g., MERN, MEAN, Cloud, DevOps)
   - Missing core CS subjects (e.g., OS, DBMS, System Design, Computer Networks)
4. List specific actionable suggestions for each candidate to get selected.

Return valid JSON ONLY with this structure:
{{
  "top_candidate_label": "Resume 1 (or candidate name/filename)",
  "top_candidate_filename": "<filename>",
  "winner_announcement": "<Clear statement explaining why this resume won and is better than the rest>",
  "candidates": [
    {{
      "display_name": "Resume 1: <filename>",
      "filename": "<filename>",
      "ats_score": 85,
      "match_verdict": "High Match",
      "matched_skills": ["skill1", "skill2"],
      "missing_languages_tools": ["e.g. Java, Python"],
      "missing_stacks_domains": ["e.g. MERN, MEAN"],
      "missing_core_subjects": ["e.g. OS, DBMS"],
      "how_to_get_shortlisted": [
        "Action 1",
        "Action 2"
      ]
    }}
  ]
}}
"""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return response.text

# --- Main App UI ---
st.title("📊 Multi-Resume ATS Comparison & Gap Analyzer")
st.write("Upload 1, 2, or 3 resumes against a Job Description to rank them and identify missing tech stacks.")

col_jd, col_res = st.columns([1, 1])

with col_jd:
    st.subheader("1. Job Description (JD)")
    jd_input = st.text_area("Paste Job Description:", height=220, placeholder="Paste JD requirements (e.g. MERN stack, OS, DBMS, Python, Docker)...")

with col_res:
    st.subheader("2. Candidate Resumes")
    uploaded_files = st.file_uploader("Upload Resumes (PDF / TXT)", type=["pdf", "txt"], accept_multiple_files=True)
    if uploaded_files:
        st.success(f"Loaded {len(uploaded_files)} resume file(s).")

if "eval_results" not in st.session_state:
    st.session_state.eval_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "full_context" not in st.session_state:
    st.session_state.full_context = ""

if st.button("🚀 Compare Resumes & Generate ATS Graph", type="primary", use_container_width=True):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar or in your .env file.")
    elif not jd_input.strip():
        st.error("Please provide the Job Description.")
    elif not uploaded_files:
        st.error("Please upload at least one Resume.")
    else:
        with st.spinner("Scoring resumes and preparing graphical comparison..."):
            try:
                client = genai.Client(api_key=api_key)
                resumes_dict = {}
                for idx, f in enumerate(uploaded_files, start=1):
                    display_key = f"Resume {idx} ({f.name})"
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
                    "content": f"I've ranked all resumes! **{data.get('top_candidate_label', 'Top Candidate')}** has the highest ATS score. Ask me how other candidates can bridge the gap."
                }]
            except errors.ClientError as e:
                if "429" in str(e):
                    st.error("⚠️ Quota limit reached on free tier. Please wait 30–60 seconds and retry.")
                else:
                    st.error(f"Gemini API Error: {str(e)}")
            except Exception as e:
                st.error(f"Error analyzing resumes: {str(e)}")

# --- Results Presentation ---
if st.session_state.eval_results:
    data = st.session_state.eval_results
    candidates = sorted(data.get("candidates", []), key=lambda x: x.get("ats_score", 0), reverse=True)
    winner = candidates[0] if candidates else {}

    st.markdown("---")

    # 🏆 Winner Banner
    st.success(
        f"### 🏆 **{winner.get('display_name', 'Top Candidate')} is the Best Match!**\n"
        f"**Highest ATS Score:** `{winner.get('ats_score')}%` | **Verdict:** `{winner.get('match_verdict')}`\n\n"
        f"**Why it's better:** {data.get('winner_announcement', '')}"
    )

    # 📈 Interactive ATS Score Comparison Graph
    st.subheader("📈 ATS Score Comparison Chart")
    
    df_chart = pd.DataFrame([
        {
            "Resume": c.get("display_name", c.get("filename")),
            "ATS Score (%)": c.get("ats_score", 0),
            "Verdict": c.get("match_verdict", "N/A")
        }
        for c in candidates
    ])

    fig = px.bar(
        df_chart,
        x="Resume",
        y="ATS Score (%)",
        text="ATS Score (%)",
        color="ATS Score (%)",
        color_continuous_scale="Blues",
        range_y=[0, 100],
        title="Candidate ATS Fit Comparison"
    )
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.update_layout(xaxis_title="Candidates", yaxis_title="ATS Score (0 - 100)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 🔍 Detailed Breakdown per Resume
    st.markdown("---")
    st.subheader("🔍 Individual Gap Breakdown & Improvement Suggestions")

    for idx, c in enumerate(candidates, start=1):
        is_top = (idx == 1)
        tag = " 🌟 [TOP MATCH]" if is_top else ""
        with st.expander(f"📄 {c.get('display_name', c.get('filename'))} — ATS Score: {c.get('ats_score')}% {tag}", expanded=is_top):
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### ✅ Matched Skills & Keywords")
                if c.get("matched_skills"):
                    st.write(", ".join([f"`{s}`" for s in c.get("matched_skills")]))
                else:
                    st.write("No direct keyword matches.")

                st.markdown("#### ⚠️ Missing Technologies & Domains")
                st.write(f"- **Languages / Tools:** {', '.join(c.get('missing_languages_tools', [])) or 'None'}")
                st.write(f"- **Domains / Full Stack (MERN/MEAN):** {', '.join(c.get('missing_stacks_domains', [])) or 'None'}")
                st.write(f"- **Core CS Subjects (OS, DBMS, CN):** {', '.join(c.get('missing_core_subjects', [])) or 'None'}")

            with col_right:
                st.markdown("#### 🎯 Must Add to Get Shortlisted")
                for step in c.get("how_to_get_shortlisted", []):
                    st.markdown(f"- {step}")

    # 💬 Interactive Chat
    st.markdown("---")
    st.subheader("💬 Ask ATS Bot for Suggestions")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input("Ask how candidate 2 can improve its score to beat candidate 1..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    client = genai.Client(api_key=api_key)
                    chat_res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=f"Context:\n{st.session_state.full_context}\n\nQuestion: {query}\nProvide concise, direct ATS recruiter feedback."
                    )
                    reply = chat_res.text
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except errors.ClientError as e:
                    if "429" in str(e):
                        err_msg = "⚠️ Quota limit reached. Please wait ~30 seconds before sending another chat message."
                    else:
                        err_msg = f"Chat error: {e}"
                    st.warning(err_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": err_msg})