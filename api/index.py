import os
import io
import re
import json
import time
import random
import zipfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler
import email
from email import policy
import pypdf
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_gemini_client():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not configured.")
    return genai.Client(api_key=GEMINI_API_KEY)

def extract_docx(file_bytes: bytes) -> str:
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
    fn = filename.lower()
    text = ""
    try:
        if fn.endswith(".pdf"):
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                pt = page.extract_text()
                if pt:
                    text += pt + "\n"
        elif fn.endswith(".docx"):
            text = extract_docx(file_bytes)
        elif fn.endswith(".doc"):
            raw = file_bytes.decode("latin-1", errors="ignore")
            blocks = re.findall(r'[a-zA-Z0-9.,;:!?/@#%&()\-_+=\n ]{4,}', raw)
            text = " ".join([b.strip() for b in blocks if len(b.strip()) > 3])
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return "", False

    cleaned = text.strip()
    return cleaned, len(cleaned) >= 50

def clean_json_string(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()

def run_evaluation(jd_text: str, candidates_payload: str) -> dict:
    client = get_gemini_client()
    prompt = f"""
You are an expert ATS recruitment evaluator and technical resume coach.
Analyze each candidate strictly against the Job Description AND conduct a practical resume improvement audit.

JOB DESCRIPTION:
{jd_text}

RESUMES:
{candidates_payload}

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
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            if resp and resp.text:
                cleaned = clean_json_string(resp.text)
                return json.loads(cleaned)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                retry_match = re.search(r"retry in ([\d\.]+)s", err, re.IGNORECASE)
                sleep_sec = float(retry_match.group(1)) + 1.0 if retry_match else 25.0
                time.sleep(sleep_sec)
            else:
                time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
    raise RuntimeError("Failed to obtain response from Gemini API after retries.")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_type = self.headers.get('content-type', '')
            content_length = int(self.headers.get('content-length', 0))
            body_bytes = self.rfile.read(content_length)

            if 'multipart/form-data' not in content_type:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Multipart form data required"}')
                return

            # Native, deprecation-free email parser for multipart payload
            msg_data = f"Content-Type: {content_type}\r\n\r\n".encode('latin-1') + body_bytes
            parsed_msg = email.message_from_bytes(msg_data, policy=policy.default)

            jd = ""
            payload = ""

            for part in parsed_msg.iter_parts():
                cd = part.get("Content-Disposition", "")
                if 'name="jd"' in cd:
                    jd = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif 'filename=' in cd:
                    filename = part.get_filename() or "uploaded_file"
                    file_bytes = part.get_payload(decode=True)
                    text, valid = extract_text(file_bytes, filename)
                    if valid:
                        payload += f"\n--- CANDIDATE: {filename} ---\n{text[:11000]}\n"

            if not jd.strip():
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Job description is missing"}')
                return

            if not payload.strip():
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "No valid text could be extracted from uploaded resumes"}')
                return

            result = run_evaluation(jd, payload)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))