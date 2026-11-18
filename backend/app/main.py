"""TERRALERT starter API. No hazard predictions are generated until verified inputs exist."""
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="TERRALERT API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["GET"], allow_headers=["*"])
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "terralert-api"}

@app.get("/api/db-health")
def db_health():
    try:
        import psycopg
        with psycopg.connect(os.environ.get("DATABASE_URL", "postgresql://terralert:change_me@localhost:5432/terralert"), connect_timeout=3) as con:
            with con.cursor() as cur:
                cur.execute("SELECT PostGIS_Version()")
                version = cur.fetchone()[0]
        return {"status": "ok", "postgis_version": version}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {type(exc).__name__}")

@app.get("/api/communes")
def communes():
    path = DATA_DIR / "communes.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Add the team's validated 11-commune GeoJSON at data/communes.geojson")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("type") != "FeatureCollection":
            raise ValueError("Expected GeoJSON FeatureCollection")
        return JSONResponse(payload)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
