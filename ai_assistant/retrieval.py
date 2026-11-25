#!/usr/bin/env python3
"""TERRALERT local scientific document retrieval."""

import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that",
    "what", "which", "how", "does", "are", "was", "were",
    "dans", "avec", "pour", "les", "des", "une", "est",
    "sur", "qui", "que", "comment", "quel", "quelle",
    "de", "du", "la", "le", "un", "en", "et", "to",
    "of", "in", "a", "is", "do", "we", "our",
}

def tokenize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(
        c for c in text if not unicodedata.combining(c)
    )
    # Normalize compound weather terms before tokenization.
    text = re.sub(r"\bcoldwaves?\b", "cold waves", text)
    text = re.sub(r"\bheatwaves?\b", "heat waves", text)

    return [
        w for w in re.findall(r"[a-z0-9]+", text)
        if len(w) > 2 and w not in STOPWORDS
    ]

def load_documents():
    chunks = []

    for path in sorted(DOCS.glob("*.md")):
        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()

        section = path.stem
        buffer = []
        start_line = 1

        def save_chunk():
            if buffer:
                content = "\n".join(buffer).strip()
                if content:
                    chunks.append({
                        "source": str(path.relative_to(ROOT)),
                        "section": section,
                        "line": start_line,
                        "text": content,
                    })

        for line_number, line in enumerate(lines, 1):
            if line.startswith("#"):
                save_chunk()
                buffer = []
                section = line.lstrip("# ").strip()
                start_line = line_number
            elif not buffer:
                start_line = line_number

            buffer.append(line)

            if len(buffer) >= 16:
                save_chunk()
                buffer = []
                start_line = line_number + 1

        save_chunk()

    return chunks

def search(question, top_k=3):
    documents = load_documents()

    if not documents:
        return []

    query_terms = set(tokenize(question))
    if not query_terms:
        return []

    vectors = [Counter(tokenize(d["text"])) for d in documents]
    document_frequency = Counter()

    for vector in vectors:
        document_frequency.update(vector.keys())

    scored = []
    n = len(documents)

    for document, vector in zip(documents, vectors):
        score = 0.0

        for term in query_terms:
            frequency = vector.get(term, 0)
            if frequency:
                idf = math.log(
                    (n + 1) /
                    (document_frequency[term] + 1)
                ) + 1
                score += (
                    (1 + math.log(frequency)) * idf
                )

        # Give relevant section headings a modest boost.
        heading_terms = set(tokenize(document["section"]))
        score += 0.5 * len(query_terms & heading_terms)

        if score > 0:
            scored.append((score, document))

    # Restrict results to the risk topic when identifiable.
    topic_terms = {
        "heatwave": (
            "heat", "heatwave", "heatwaves", "canicule",
            "weather_extremes"
        ),
        "coldwave": (
            "cold", "coldwave", "coldwaves", "froid",
            "weather_extremes"
        ),
        "wildfire": ("wildfire", "wildfires", "fwi", "fire"),
        "rainfall": ("rainfall", "precipitation", "pluie"),
    }

    question_tokens = set(tokenize(question))

    selected_topics = [
        topic for topic, words in topic_terms.items()
        if question_tokens.intersection(words)
    ]

    if selected_topics:
        filtered = []

        for score, document in scored:
            filename = document["source"].lower()

            if any(
                any(word in filename for word in topic_terms[topic])
                for topic in selected_topics
            ):
                filtered.append((score, document))

        scored = filtered

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        {"score": round(score, 3), **document}
        for score, document in scored[:top_k]
    ]

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        question = (
            "How does TERRALERT validate wildfire danger?"
        )

    print("=== TERRALERT DOCUMENT RETRIEVAL ===")
    print("Question:", question)
    print("Documents:", len(list(DOCS.glob("*.md"))))

    results = search(question)

    if not results:
        print("\nNo matching scientific passage found.")
    else:
        for i, result in enumerate(results, 1):
            print(f"\n=== SOURCE {i} ===")
            print("File:", result["source"])
            print("Section:", result["section"])
            print("Starting line:", result["line"])
            print("Relevance score:", result["score"])
            print(
                "Passage:",
                result["text"][:700]
            )
