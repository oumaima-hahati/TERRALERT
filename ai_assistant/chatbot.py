#!/usr/bin/env python3
"""TERRALERT grounded chatbot prototype (no LLM yet)."""

import json
import re
import sys

if __package__:
    from .data_queries import query as query_data
    from .retrieval import search as search_docs
    from .llm_adapter import generate
else:
    from data_queries import query as query_data
    from retrieval import search as search_docs
    from llm_adapter import generate


def normalize_question(question):
    return question.strip().lower()


def is_methodology_question(question):
    q = normalize_question(question)

    patterns = [
        r"\bhow (does|do|are|is)\b",
        r"\bmethodolog",
        r"\bexplain\b",
        r"\bdefinition\b",
        r"\bthreshold",
        r"\bvalidate\b",
        r"\bvalidation\b",
        r"\bcomment\b",
        r"\bméthod",
        r"\bmethode\b",
        r"\bexpliqu",
        r"\bdéfini",
        r"\bseuil",
        r"\bcalcul",
    ]

    return any(re.search(p, q) for p in patterns)


def answer(question):
    question = question.strip()

    if not question:
        return {
            "status": "INVALID_QUESTION",
            "answer": "Please enter a question."
        }

    if is_methodology_question(question):
        passages = search_docs(question, top_k=3)

        if not passages:
            return {
                "status": "NO_DOCUMENT_MATCH",
                "answer": (
                    "I could not find supporting information "
                    "in the TERRALERT scientific documentation."
                ),
                "sources": [],
            }

        top = passages[0]

        generated = generate(question, top["text"])

        return {
            "status": "SUCCESS",
            "mode": "DOCUMENT_RETRIEVAL",
            "answer": generated["answer"],
            "generation_mode": generated["mode"],
            "llm_used": generated["llm_used"],
            "sources": [
                {
                    "file": p["source"],
                    "section": p["section"],
                    "starting_line": p["line"],
                    "score": p["score"],
                }
                for p in passages
            ],
            "note": (
                "Retrieved source passage, not an "
                "AI-generated interpretation."
            ),
        }

    try:
        data = query_data(question)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        return {
            "status": "DATA_ERROR",
            "answer": str(exc),
            "sources": [],
        }

    if data["status"] == "SUCCESS":
        return {
            "status": "SUCCESS",
            "mode": "STRUCTURED_DATA",
            "answer": data["answer"],
            "sources": [{
                "file": data["source_file"],
                "type": "TERRALERT_DATASET",
            }],
            "data": data,
        }

    return {
        "status": data["status"],
        "answer": data["answer"],
        "sources": [],
    }


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])

    if not question:
        raise SystemExit(
            'Usage: python ai_assistant/chatbot.py "question"'
        )

    print(json.dumps(
        answer(question),
        indent=2,
        ensure_ascii=False
    ))
