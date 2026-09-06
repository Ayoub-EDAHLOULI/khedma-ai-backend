import json

from openai import OpenAI

from app.config import settings
from app.models import Job, Profile

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a career assistant helping a candidate apply to a specific job.

Given the candidate's real CV text and the job description, produce:
1. A tailored CV summary: rewrite/reorder the candidate's existing experience and skills
   to foreground what's most relevant to THIS job. Never invent experience, skills, or
   qualifications the candidate does not already have in their CV text.
2. A cover letter (3-4 short paragraphs) that references 2-3 concrete overlaps between
   the job description and the candidate's real background.

Respond ONLY with a JSON object: {"tailored_cv": "...", "cover_letter": "..."}"""


def write_application(profile: Profile, job: Job) -> dict:
    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = json.dumps(
        {
            "candidate_cv": profile.cv_text,
            "candidate_skills": profile.skills,
            "job_title": job.title,
            "company": job.company,
            "job_description": job.description,
        }
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)
