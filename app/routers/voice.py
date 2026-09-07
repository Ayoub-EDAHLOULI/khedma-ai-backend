import datetime

from fastapi import APIRouter
from google import genai
from google.genai import types

from app.config import settings
from app.response import ApiResponse
from app.schemas import VoiceSessionTokenResponse

router = APIRouter(prefix="/voice", tags=["voice"])

# Gemini Live integration (see CLAUDE.md "Future direction — Voice
# conversation"). This mints a short-lived, single-use token server-side so
# the raw Gemini API key never reaches the browser — same pattern as
# OpenAI's Realtime API ephemeral keys.
SESSION_MINUTES = 30
NEW_SESSION_WINDOW_MINUTES = 1

# Must mirror the frontend's SEARCH_JOBS_DECLARATION in
# useGeminiLiveVoice.ts exactly (name, description, schema) — it's unclear
# from Gemini's docs whether a client-supplied `tools` config at connect
# time merges with or is overridden by the token's own locked config, so we
# declare the same tool in both places to not depend on that behavior.
SEARCH_JOBS_DECLARATION = types.FunctionDeclaration(
    name="search_jobs",
    description=(
        "Search the user's already-ingested job postings for matches. Call "
        "this whenever the user asks to find, search for, or look up jobs — "
        "pass a natural-language query summarizing what they want, in the "
        "language they used. Only set scope/remote_only/country/seniority "
        "when the user was explicit about them."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Natural-language summary of the job the user is "
                    "looking for, in the user's own language (e.g. 'junior "
                    "software engineer jobs in the UK')."
                ),
            },
            "scope": {
                "type": "string",
                "enum": ["local", "international"],
                "description": "Only set if the user explicitly said local or international.",
            },
            "remote_only": {
                "type": "boolean",
                "description": "Only set true if the user explicitly asked for remote-only jobs.",
            },
            "country": {
                "type": "string",
                "description": "ISO 3166-1 alpha-2 country code, only if the user named a specific country.",
            },
            "seniority": {
                "type": "string",
                "enum": ["junior", "mid", "senior"],
                "description": "Only set if the user explicitly implied a seniority level.",
            },
        },
        "required": ["query"],
    },
)


@router.post("/session-token", response_model=ApiResponse[VoiceSessionTokenResponse])
def create_voice_session_token():
    client = genai.Client(api_key=settings.gemini_api_key)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    expire_time = now + datetime.timedelta(minutes=SESSION_MINUTES)

    token = client.auth_tokens.create(
        config=types.CreateAuthTokenConfig(
            uses=1,
            expire_time=expire_time,
            new_session_expire_time=now
            + datetime.timedelta(minutes=NEW_SESSION_WINDOW_MINUTES),
            live_connect_constraints=types.LiveConnectConstraints(
                model=settings.gemini_live_model,
                config=types.LiveConnectConfig(
                    response_modalities=[types.Modality.AUDIO],
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                    tools=[
                        types.Tool(function_declarations=[SEARCH_JOBS_DECLARATION])
                    ],
                ),
            ),
        )
    )

    result = VoiceSessionTokenResponse(
        token=token.name,
        model=settings.gemini_live_model,
        expire_time=expire_time,
    )
    return ApiResponse.ok(result, "Voice session token created")
