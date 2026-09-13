import os
import io
import re
import json
import time
import html
import zipfile
import xml.etree.ElementTree as ET
import pypdf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from your .env file.")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing from your .env file.")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

def extract_docx_native(file_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            xml_content = docx_zip.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [node.text for node in tree.iterfind('.//w:t', namespaces) if node.text]
            return " ".join(texts)
    except Exception as e:
        print(f"DOCX Extraction error: {e}")
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
        print(f"Extraction error for {filename}: {e}")
    return text.strip()

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
                print(f"[API Retrying] Model: {model_name} | Attempt: {attempt+1} | Error: {e}")
                time.sleep((2 ** attempt) + 1)
                continue
    raise RuntimeError(f"All Gemini models failed: {last_err}")

def generate_ats_chart(candidates):
    names = [c.get("name", "Candidate") for c in candidates]
    scores = [c.get("score", 0) for c in candidates]

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=180)
    fig.patch.set_facecolor('#0b0f19')
    ax.set_facecolor('#111827')

    colors = ['#22c55e' if s >= 75 else '#38bdf8' if s >= 50 else '#f43f5e' for s in scores]
    bars = ax.barh(names, scores, color=colors, height=0.5, edgecolor='none')

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 2,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width)}%",
            va='center',
            ha='left',
            color='#f1f5f9',
            fontweight='bold',
            fontsize=10
        )

    ax.set_xlim(0, 115)
    ax.set_xlabel("ATS Fit Score (%)", color='#94a3b8', fontsize=9, fontweight='bold', labelpad=6)
    ax.set_title("MatchPro ATS Benchmark Comparison", color='#38bdf8', fontsize=12, fontweight='bold', pad=12)
    ax.tick_params(colors='#94a3b8', labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#1e293b')
    ax.spines['bottom'].set_color('#1e293b')
    ax.grid(axis='x', color='#1e293b', linestyle='--', alpha=0.5)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf

async def send_welcome_guide(update: Update):
    msg = (
        "👋 <b>Welcome to MatchPro ATS Bot!</b>\n\n"
        "1️⃣ <b>Set Job Requirements:</b> Send <code>/jd &lt;job description text&gt;</code>\n"
        "2️⃣ <b>Upload Resumes:</b> Send 1 or more candidate files (<code>.pdf</code>, <code>.docx</code>, <code>.doc</code>, <code>.txt</code>).\n"
        "3️⃣ <b>Evaluate:</b> Send <code>/compare</code> to benchmark this batch.\n"
        "4️⃣ <b>Reset:</b> Send <code>/clear</code> to wipe staged files."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def execute_evaluation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jd = context.user_data.get("jd", "")
    resumes = context.user_data.get("resumes", {})

    if not resumes:
        await update.message.reply_text("⚠️ No staged resumes found. Please upload candidate resume(s) first.", parse_mode=ParseMode.HTML)
        return
    if not jd:
        await update.message.reply_text("⚠️ Please set a Job Description first using <code>/jd &lt;text&gt;</code>.", parse_mode=ParseMode.HTML)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    status_msg = await update.message.reply_text(f"⚡ <b>Benchmarking {len(resumes)} candidate(s) against current JD...</b>", parse_mode=ParseMode.HTML)
    
    payload = ""
    for name, content in resumes.items():
        payload += f"\n--- CANDIDATE: {name} ---\n{content[:2500]}\n"

    prompt = f"""
You are an expert ATS recruitment evaluator.
Analyze each candidate strictly against the Job Description.

JOB DESCRIPTION:
{jd}

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

        if candidates_data:
            chart_img = generate_ats_chart(candidates_data)
            await update.message.reply_photo(
                photo=chart_img,
                caption="📊 <b>Candidate ATS Match Benchmark</b>",
                parse_mode=ParseMode.HTML
            )

        for rep in reports:
            name = html.escape(str(rep.get("name", "Candidate")))
            score = rep.get("score", 0)
            cat = html.escape(str(rep.get("score_category", "")))
            icon = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"

            matched_s = ", ".join([f"✅ {html.escape(s)}" for s in rep.get("skills", {}).get("matched", [])]) or "None"
            partial_s = ", ".join([f"⚡ {html.escape(s)}" for s in rep.get("skills", {}).get("partial", [])]) or "None"
            missing_s = ", ".join([f"❌ {html.escape(s)}" for s in rep.get("skills", {}).get("missing", [])]) or "None"

            sb = rep.get("score_breakdown", {})
            gaps_text = "\n  ".join([f"{html.escape(g)}" for g in rep.get("gaps", [])])

            courses_text = ""
            for c in rep.get("course_suggestions", []):
                title = html.escape(str(c.get("title", "Course")))
                url = html.escape(str(c.get("url", "https://coursera.org")))
                desc = html.escape(str(c.get("desc", "")))
                courses_text += f"  • 📚 <a href='{url}'>{title}</a> — {desc}\n"

            msg_html = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Candidate:</b> {name}
{icon} <b>ATS Score:</b> {score}% ({cat})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Score Breakdown:</b>
  • Skills: {sb.get('skills', 'N/A')}
  • Experience: {sb.get('experience', 'N/A')}
  • Projects/Responsibilities: {sb.get('projects', 'N/A')}
  • Education: {sb.get('education', 'N/A')}
  • Keyword Match: {sb.get('keywords', 'N/A')}

🎯 <b>Skill Alignment:</b>
  <b>Matched:</b> {matched_s}
  <b>Partial:</b> {partial_s}
  <b>Missing:</b> {missing_s}

⏳ <b>Experience Match:</b>
  • {html.escape(str(rep.get('experience_match', 'N/A')))}

🎓 <b>Education Match:</b>
  • {html.escape(str(rep.get('education_match', 'N/A')))}

⚠️ <b>Gaps &amp; Weaknesses:</b>
  {gaps_text}

🚀 <b>Recommended Next Steps / Learning:</b>
{courses_text}"""

            await update.message.reply_text(
                msg_html,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
            
        await status_msg.delete()

        context.user_data["resumes"] = {}
        await update.message.reply_text(
            "✨ <b>Batch Completed!</b> Staged resumes have been cleared.\n"
            "Upload new resume(s) for your next evaluation.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error during evaluation: {html.escape(str(e))}", parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["jd"] = ""
    context.user_data["resumes"] = {}
    await send_welcome_guide(update)

async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["resumes"] = {}
    context.user_data["jd"] = ""
    await update.message.reply_text("🧹 <b>Workspace reset!</b> Both JD and staged resumes have been cleared.", parse_mode=ParseMode.HTML)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    extracted = extract_text(bytes(file_bytes), doc.file_name)
    if "resumes" not in context.user_data:
        context.user_data["resumes"] = {}
        
    context.user_data["resumes"][doc.file_name] = extracted
    count = len(context.user_data["resumes"])
    
    await update.message.reply_text(
        f"📄 <b>Resume Saved:</b> <code>{html.escape(doc.file_name)}</code> ({count} in current batch).\n\n"
        f"👉 Send <code>/compare</code> when ready, or upload more resumes.",
        parse_mode=ParseMode.HTML
    )

async def set_jd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jd_text = " ".join(context.args)
    if not jd_text:
        await update.message.reply_text(
            "⚠️ Please provide text after <code>/jd</code>. Example:\n"
            "<code>/jd Senior Python Developer with FastAPI and Docker</code>", 
            parse_mode=ParseMode.HTML
        )
        return
    
    context.user_data["jd"] = jd_text
    current_resumes = len(context.user_data.get("resumes", {}))
    
    await update.message.reply_text(
        f"✅ <b>Job Description saved!</b>\n"
        f"📁 Currently staged resumes: <b>{current_resumes}</b>\n\n"
        f"👉 Upload more resumes or send <code>/compare</code> to benchmark.",
        parse_mode=ParseMode.HTML
    )

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await execute_evaluation(update, context)

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip().lower()
    
    if user_msg in ["compare", "analyze", "benchmark"]:
        await execute_evaluation(update, context)
        return

    if user_msg in ["clear", "reset"]:
        await handle_clear(update, context)
        return

    if re.search(r'\b(hi|hello|hey|greetings|morning|afternoon|evening)\b', user_msg):
        await update.message.reply_text(
            "👋 <b>Hello there!</b> I'm your MatchPro ATS Assistant.\n\n"
            "Ready to screen resumes? Upload candidate files or set your JD using <code>/jd &lt;text&gt;</code>.",
            parse_mode=ParseMode.HTML
        )
        return

    if re.search(r'\b(how are you|how r u|how is it going|how are things)\b', user_msg):
        await update.message.reply_text(
            "⚡ <b>I'm running at 100% capacity and ready to rank some top talent!</b>\n\n"
            "Drop your candidate resumes and let's find the best match.",
            parse_mode=ParseMode.HTML
        )
        return

    if re.search(r'\b(who are you|what can you do|what are you|who r u)\b', user_msg):
        msg = (
            "🤖 <b>About MatchPro ATS Bot:</b>\n\n"
            "I'm an AI recruitment engine designed to benchmark candidate resumes against target job descriptions.\n\n"
            "✨ <b>What I do:</b>\n"
            "• Extract and analyze <code>.pdf</code>, <code>.docx</code>, <code>.doc</code>, and <code>.txt</code> resumes\n"
            "• Score candidate fit (0–100%) against specific JD requirements\n"
            "• Detect missing languages, domains (MERN/Cloud), and Core CS subjects\n"
            "• Generate visual benchmark comparison charts\n"
            "• Recommend curated upskilling courses for identified gaps"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    await send_welcome_guide(update)

if __name__ == "__main__":
    request_config = HTTPXRequest(
        connect_timeout=45.0,
        read_timeout=45.0,
        write_timeout=45.0,
        pool_timeout=45.0
    )

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request_config)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(CommandHandler("reset", handle_clear))
    app.add_handler(CommandHandler("jd", set_jd))
    app.add_handler(CommandHandler("analyze", run_analysis))
    app.add_handler(CommandHandler("compare", run_analysis))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_chat))
    
    print("🤖 MatchPro ATS Bot is running smoothly...")
    app.run_polling(drop_pending_updates=True)