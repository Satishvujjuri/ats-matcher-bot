# ⚡ MatchPro ATS — AI-Powered Recruiter Intelligence Engine

MatchPro ATS is an AI-driven recruitment screening and benchmarking assistant powered by Google Gemini (`gemini-2.5-flash` / `gemini-3.6-flash`). It provides dual-interface accessibility via a **Telegram Bot** for on-the-go recruitment workflows and a **Streamlit Web Dashboard** for desktop evaluation.

The engine parses multi-format candidate resumes, evaluates contextual alignment against specific Job Descriptions (JDs), generates visual fit charts, identifies gaps in technical stacks and core CS fundamentals, and delivers actionable upskilling pathways with verified course hyperlinks.

---

## ✨ Key Features

* **Multi-Format Resume Ingestion:** Parses `.pdf`, `.docx`, `.doc`, and `.txt` files using a native OpenXML/ZIP extraction pipeline (zero binary DLL dependencies to ensure compatibility across all operating systems).
* **Contextual ATS Scoring (0–100%):** Evaluates candidate depth across skills, work history, projects, and education rather than relying on simple keyword matching.
* **Batch Comparative Benchmarking:** Ingests multiple candidate resumes simultaneously to rank profiles and generate comparative visual bar charts.
* **Core Subject & Skill Gap Analysis:** Detects missing technologies, architectural patterns, and foundational CS topics (OS, DBMS, Computer Networks, System Design).
* **Actionable Upskilling Pathways:** Generates curated learning roadmaps featuring direct, hyperlinked courses from platforms such as Coursera, Udemy, and edX.
* **Dual Deployment Interface:**
  * **Telegram Bot:** Lightweight mobile screening with automated staging queues, commands (`/jd`, `/compare`, `/clear`), and inline visualizations.
  * **Streamlit Dashboard:** Recruiter workbench with score distributions, candidate comparison matrices, and an integrated contextual gap chat assistant.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **LLM Core:** Google GenAI SDK (`gemini-2.5-flash` / `gemini-3.6-flash`)
* **Interfaces:** `python-telegram-bot`, `streamlit`
* **Data & Visualization:** `pandas`, `plotly`, `matplotlib`
* **Parsing Engine:** `pypdf`, Python Native `zipfile` & `xml.etree.ElementTree`
* **Configuration:** `python-dotenv`

---

## 📁 Repository Structure

```text
├── app.py               # Streamlit Recruiter Dashboard
├── new_telegram.py      # Telegram ATS Recruiter Bot
├── requirements.txt     # Project dependencies
├── .env.example         # Template for environment variables
└── README.md            # Documentation
