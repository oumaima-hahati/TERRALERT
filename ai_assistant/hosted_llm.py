"""Optional OpenAI-compatible hosted LLM connector."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Fixed HTTPS endpoint; no user-supplied URL.
API_URL = "https://api.openai.com/v1/chat/completions"


class HostedLLMError(Exception):
    """Hosted model request failed."""


def generate_hosted(question, evidence):
    """
    Generate an evidence-grounded explanation.

    Must be explicitly enabled with environment variables.
    Does not verify factual correctness of generated text.
    """

    key = os.getenv("TERRALERT_OPENAI_API_KEY", "").strip()
    model = os.getenv("TERRALERT_OPENAI_MODEL", "").strip()

    if not key or not model:
        raise HostedLLMError(
            "Hosted AI is not configured. "
            "API key and model are required."
        )

    if not question.strip() or not evidence.strip():
        raise HostedLLMError(
            "Question and supporting evidence are required."
        )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the TERRALERT research GIS assistant. "
                    "Use only the supplied evidence. "
                    "Never invent environmental values. "
                    "Distinguish historical observations from "
                    "forecasts and preserve dates and units. "
                    "Do not present research outputs as official "
                    "emergency warnings. "
                    "If evidence is insufficient, say so."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Supporting evidence:\n{evidence}"
                ),
            },
        ],
    }

    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)

        answer = result["choices"][0]["message"]["content"]

        if not isinstance(answer, str) or not answer.strip():
            raise HostedLLMError("Empty model response")

        return {
            "mode": "HOSTED_LLM",
            "answer": answer.strip(),
            "llm_used": True,
            "model": model,
            "verification_required": True,
        }

    except (HTTPError, URLError, TimeoutError) as exc:
        raise HostedLLMError(
            "Hosted AI request failed"
        ) from exc

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HostedLLMError(
            "Invalid hosted AI response"
        ) from exc
