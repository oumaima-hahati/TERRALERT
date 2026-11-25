# TERRALERT — AI GIS Chatbot & RAG Assistant

## Status

Standalone research prototype.

The assistant currently combines:
- Scientific document retrieval
- Structured environmental data queries
- A standalone FastAPI endpoint
- An optional local LLM adapter

Actual LLM inference has not yet been tested.
The default mode is retrieval-only.

## Supported questions

### Scientific methodology
Retrieves relevant passages from TERRALERT Markdown
documentation, including source references.

### Rainfall forecasts
Returns 24h/72h rainfall estimates from Open-Meteo
forecast summaries.

### Wildfire danger
Returns provisional Fire Weather Index (FWI)
values and danger categories.

### Heatwaves
Returns historical heatwave statistics and
2024 population-based exposure indicators.

### Cold waves
Returns historical cold-wave statistics and
elevation indicators.

## API

Endpoint:

POST /chatbot/ask

Example request:

{
  "question": "Rainfall Gueznaia 72h"
}

Responses include an answer, status and source references.

## Running locally

From the TERRALERT project root:

    backend/.venv/bin/uvicorn ai_assistant.standalone:app --port 8001

Interactive API documentation:

    http://127.0.0.1:8001/docs

The standalone application does not modify
the main TERRALERT FastAPI backend.

## Automated tests

From the project root:

    backend/.venv/bin/python -m unittest discover \
      -s ai_assistant/tests -p 'test_*.py' -v

Latest result: 9/9 tests passed.

## Optional LLM

The LLM adapter supports a local Ollama endpoint.

By default, LLM generation is disabled.

To enable it later, an Ollama model must be installed
and its output must be scientifically evaluated.

Configuration:

    TERRALERT_LLM_ENABLED=1
    TERRALERT_LLM_MODEL=<installed_model_name>

Do not enable untested generated responses
for public environmental warnings.

## Scientific limitations

- Forecast outputs are provisional research results.
- Forecasts must be interpreted using their dates.
- Historical exposure is not observed human impact.
- Document retrieval is keyword-based, not semantic.
- The assistant does not perform arbitrary spatial SQL.
- No independent verification of LLM-generated text.
- No public emergency alerts are generated.
- React integration remains pending.
- PostGIS integration remains pending.

## Dependencies

Python standard library for core retrieval.

FastAPI and Pydantic for the standalone API.

The HTTP regression tests use the backend
virtual environment's testing dependencies.

## Integration

The standalone API can later be integrated into
TERRALERT's existing backend and React interface.

Coordinate changes to the main FastAPI application
and frontend with the responsible teammate.
