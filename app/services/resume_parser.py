import io
import json

import pdfplumber
from docx import Document
from openai import OpenAI

from app.config import settings

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a resume-parsing assistant. Given the raw text extracted
from a candidate's resume (PDF or Word), extract structured fields.

Never invent information that is not present in the text. If a field genuinely
cannot be determined from the text, use an empty string or empty list for it.

Respond ONLY with a JSON object:
{
  "full_name": "...",
  "skills": ["...", ...],
  "cv_text": "..."
}

"cv_text" should be a cleaned-up, plain-text version of the resume's experience/
summary section — reformatted for readability (no page-break artifacts, no
repeated headers/footers) but not summarized or shortened; keep the candidate's
own content and wording.
"""


class UnsupportedFileTypeError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    if lower.endswith(".docx"):
        document = Document(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs if p.text)

    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}' — expected .pdf or .docx"
    )


def structure_resume(raw_text: str) -> dict:
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    return json.loads(response.choices[0].message.content)


def parse_resume(filename: str, content: bytes) -> dict:
    raw_text = extract_text(filename, content)
    if not raw_text.strip():
        raise ValueError("No extractable text found in this file.")

    return structure_resume(raw_text)
