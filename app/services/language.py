import json

from openai import OpenAI

from app.config import settings

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a job-search assistant. The user may write in Darija (Moroccan Arabic,
often in Latin script), Modern Standard Arabic, French, or English — sometimes
mixed. Detect the language used and note it as an ISO 639-1 code (e.g. "fr", "ar", "en";
use "ar" for Darija too, since it is written in Arabic or Latin script but is not a
separate ISO code).

From the user's message, extract a structured search query:
{
  "detected_language": "fr" | "ar" | "en" | ...,
  "role_keywords": [...],
  "skills": [...],
  "location_scope": "local" | "international" | null,
  "remote_only": boolean,
  "seniority": string | null,
  "clarifying_question": string | null
}

Set "location_scope" to null if the message does not make clear whether the user wants
local (jobs in their own country) or international (remote/visa-sponsored roles abroad)
results. When it is null, set "clarifying_question" to one short question asking them to
clarify local vs. international.

CRITICAL: if "detected_language" is "en", clarifying_question MUST be written in English.
If "detected_language" is "fr", it MUST be written in French. If "ar", in Arabic. Do not
default to French for short or ambiguous English input — English input gets an English
question. Otherwise set "clarifying_question" to null.

Respond ONLY with the JSON object described above."""


def extract_query(message: str) -> dict:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)
