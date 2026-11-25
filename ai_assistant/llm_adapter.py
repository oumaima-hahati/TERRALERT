"""Optional local LLM generation with a safe retrieval fallback."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SYSTEM_PROMPT = """
You are the TERRALERT research GIS assistant.

Answer only using the evidence provided.
Never invent environmental measurements or risk values.
Distinguish historical indicators from forecasts.
Respect the supplied forecast dates and limitations.
Never describe provisional research outputs as official alerts.
If evidence is insufficient, say so.
Respond in the language of the user's question.
"""


def generate(question, evidence):
    """Generate an answer, or return evidence without an LLM."""

    fallback = {
        "mode": "RETRIEVAL_ONLY",
        "answer": evidence,
        "llm_used": False,
    }

    if os.getenv("TERRALERT_LLM_ENABLED") != "1":
        return fallback

    model = os.getenv("TERRALERT_LLM_MODEL", "").strip()

    if not model:
        return fallback

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Retrieved evidence:\n{evidence}"
                ),
            },
        ],
        "options": {"temperature": 0},
    }

    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)

        answer = result["message"]["content"].strip()

        if not answer:
            return fallback

        return {
            "mode": "LOCAL_LLM",
            "answer": answer,
            "llm_used": True,
            "model": model,
            "verification_required": True,
        }

    except (URLError, HTTPError, KeyError, ValueError, TimeoutError):
        return fallback
