"""TERRALERT starter API. No hazard predictions are generated until verified inputs exist."""
import json
import os
import psycopg
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
    try:
        with psycopg.connect(
            os.environ["DATABASE_URL"],
            connect_timeout=5
        ) as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            json_agg(
                                json_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(
                                        ST_Transform(geom, 4326)
                                    )::json,
                                    'properties', json_build_object(
                                        'fid', fid,
                                        'nom_fr', nom_fr,
                                        'nom_ar', nom_ar,
                                        'population', p_ensemble,
                                        'densite', densite
                                    )
                                )
                                ORDER BY fid
                            ),
                            '[]'::json
                        )
                    )
                    FROM public.communes;
                """)
                result = cur.fetchone()[0]

        return JSONResponse(content=result)

    except Exception as exc:
        print(f"Database error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve commune data"
        )


@app.get("/api/rivers")
def get_rivers():
    try:
        with psycopg.connect(
            os.environ["DATABASE_URL"],
            connect_timeout=5
        ) as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            json_agg(
                                json_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::json,
                                    'properties', json_build_object(
                                        'fid', fid,
                                        'length_km', length_km,
                                        'dis_av_cms', dis_av_cms,
                                        'ord_stra', ord_stra
                                    )
                                )
                                ORDER BY fid
                            ),
                            '[]'::json
                        )
                    )
                    FROM public.rivers;
                """)
                result = cur.fetchone()[0]

        return JSONResponse(content=result)

    except Exception as exc:
        print(f"River API error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve river data"
        )
