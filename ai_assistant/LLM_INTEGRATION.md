# TERRALERT — LLM Integration

## Status

Research prototype with optional AI generation.

The assistant supports:
- Retrieval-only operation (default)
- Local Ollama connector
- Hosted OpenAI-compatible connector

No real LLM inference has been validated.
The latest regression suite passed 19 tests.

## Architecture

User question
    |
    v
Question routing
    |
    +-- Structured risk-data query
    |       |
    |       +-- Deterministic answer from CSV
    |
    +-- Scientific methodology question
            |
            +-- Retrieve documented evidence
            |
            +-- Optional LLM generation
                    |
                    +-- Provider unavailable:
                        retrieval-only fallback

## Default configuration

TERRALERT_LLM_ENABLED=0

No model, API key or external AI connection is
required for retrieval-only operation.

## Hosted AI configuration

Supported environment variables:

TERRALERT_LLM_ENABLED=1
TERRALERT_LLM_PROVIDER=hosted
TERRALERT_OPENAI_MODEL=<configured_model>
TERRALERT_OPENAI_API_KEY=<secret>

The hosted connector uses an HTTPS API.

Do not store API keys in source files,
Git commits or documentation.

Hosted inference requires explicit configuration
and may incur usage charges.

Retrieved document passages may be transmitted
to the configured external model provider.

## Local Ollama configuration

TERRALERT_LLM_ENABLED=1
TERRALERT_LLM_PROVIDER=ollama
TERRALERT_LLM_MODEL=<installed_model>

Ollama must be installed and running separately.

Local inference was not tested because the
development laptop had insufficient available RAM.

## Scientific safeguards

- Structured numerical results bypass the LLM.
- Forecast dates and sources are included in
  deterministic responses.
- Research outputs are not official alerts.
- Unsupported questions are rejected.
- Provider failures fall back to retrieved evidence.
- Document retrieval includes source references.
- Explanatory questions prioritize methodology.

## Limitations

- Document retrieval is keyword-based with
  heuristic topic and section ranking.
- Semantic embeddings are not implemented.
- Real LLM responses have not been evaluated.
- A restrictive prompt does not guarantee
  factual correctness.
- Prompt-injection resistance has not been tested.
- Real provider failures and latency remain untested.
- FastAPI router is standalone.
- Main backend and React integration are pending.
- PostGIS spatial question execution is pending.
- Authentication and production access controls
  are not implemented for the standalone endpoint.

## Automated tests

Run from the repository root:

    backend/.venv/bin/python -m unittest discover \
      -s ai_assistant/tests -p 'test_*.py' -v

Latest result: 19 tests passed.

All hosted-generation tests use mocked responses.
No real LLM inference was performed.

## Next steps

1. Evaluate real model responses against verified evidence.
2. Improve document retrieval and question coverage.
3. Add security and prompt-injection tests.
4. Coordinate backend and frontend integration.
5. Validate the complete assistant before deployment.
