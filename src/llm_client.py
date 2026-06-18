"""
llm_client.py
Unified LLM adapter for the Transcript Intake Agent.

Priority order:
  1. OpenAI      — if OPENAI_API_KEY is set in .env
  2. Copilot SDK — uses GITHUB_TOKEN from .env (or system keychain if available)

Both backends expose the same interface:
    call_llm(system_prompt, user_prompt) -> str

To enable the Copilot SDK path, add GITHUB_TOKEN to your .env file.
Generate a GitHub Personal Access Token at https://github.com/settings/tokens
with the "copilot" scope enabled.
"""

import asyncio
import json
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ── Model selection ──────────────────────────────────────────────────────────
# Override with OPENAI_MODEL (OpenAI path) or COPILOT_MODEL (Copilot path).
_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_COPILOT_MODEL = os.getenv("COPILOT_MODEL", "claude-sonnet-4.6")


def _github_token() -> str | None:
    """Return the GitHub token from env if set."""
    return os.getenv("GITHUB_TOKEN") or None


def _backend() -> str:
    """Return 'openai' if OPENAI_API_KEY is present, otherwise 'copilot'."""
    return "openai" if os.getenv("OPENAI_API_KEY") else "copilot"


# ── OpenAI path ──────────────────────────────────────────────────────────────

def _call_openai(system_prompt: str, user_prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


# ── Copilot SDK path ─────────────────────────────────────────────────────────

async def _call_copilot_async(system_prompt: str, user_prompt: str) -> str:
    token = _github_token()
    if not token:
        raise RuntimeError(
            "No GitHub token found. Add GITHUB_TOKEN=<your-pat> to your .env file. "
            "Generate a Fine-Grained PAT at https://github.com/settings/tokens with Copilot access."
        )

    from copilot import CopilotClient
    from copilot.session_events import AssistantMessageData, SessionIdleData
    from copilot.session import PermissionHandler

    full_prompt = (
        f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
        f"USER REQUEST:\n{user_prompt}\n\n"
        "Return ONLY valid JSON as instructed. No explanation. No markdown fences."
    )

    chunks: list[str] = []
    done = asyncio.Event()

    # Pass token by merging into the full system environment.
    # Using the github_token= parameter triggers COPILOT_SDK_AUTH_TOKEN
    # which is rejected for classic PATs. COPILOT_GITHUB_TOKEN is the
    # native auth path the copilot.exe binary recognizes.
    # We must pass the full env dict (not just the token) because the SDK
    # replaces the subprocess env entirely when opts.env is set (line 3202
    # of client.py: env = dict(opts.env)).
    full_env = {**os.environ, "COPILOT_GITHUB_TOKEN": token}

    async with CopilotClient(env=full_env) as client:
        async with await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model=_COPILOT_MODEL,
        ) as session:
            def on_event(event):
                match event.data:
                    case AssistantMessageData() as data:
                        if data.content:
                            chunks.append(data.content)
                    case SessionIdleData():
                        done.set()

            session.on(on_event)
            await session.send(full_prompt)
            await asyncio.wait_for(done.wait(), timeout=120)

    raw = "".join(chunks).strip()

    # Strip markdown fences if the model wrapped output anyway
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    return raw


def _call_copilot(system_prompt: str, user_prompt: str) -> str:
    token = _github_token()
    if not token:
        raise RuntimeError(
            "No GitHub token found. Add GITHUB_TOKEN=<your-pat> to your .env file. "
            "Generate a PAT at https://github.com/settings/tokens with 'copilot' scope."
        )
    return asyncio.run(_call_copilot_async(system_prompt, user_prompt))


# ── Public interface ─────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Send a prompt to the configured LLM backend. Returns the raw response string.
    Caller is responsible for JSON parsing.

    Backend selection:
      - OPENAI_API_KEY set in .env -> OpenAI API
      - GITHUB_TOKEN set in .env   -> GitHub Copilot SDK
      - Neither set                -> RuntimeError with setup instructions
    """
    backend = _backend()
    if backend == "openai":
        return _call_openai(system_prompt, user_prompt)
    else:
        return _call_copilot(system_prompt, user_prompt)


def llm_backend_name() -> str:
    """Return a display name for the active backend (for logging)."""
    backend = _backend()
    if backend == "openai":
        return f"OpenAI ({_OPENAI_MODEL})"
    token = _github_token()
    status = "token set" if token else "NO TOKEN - add GITHUB_TOKEN to .env"
    return f"GitHub Copilot SDK ({_COPILOT_MODEL}) [{status}]"
