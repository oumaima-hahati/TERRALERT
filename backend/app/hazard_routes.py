"""Read-only weather and multi-hazard API endpoints."""

import os
from datetime import date, datetime, timezone
from typing import Literal

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api")

HazardType = Literal[
    "flood", "wildfire", "heatwave", "coldwave"
]

AssessmentType = Literal[
    "susceptibility", "historical", "current", "forecast"
]


def fetch_rows(sql, params=()):
    try:
        with psycopg.connect(
            os.environ["DATABASE_URL"],
            connect_timeout=5,
            row_factory=dict_row
        ) as con:
            with con.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    except (psycopg.Error, KeyError):
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve database records"
        )


def check_dates(start, end):
    if start is not None and end is not None:
        if start > end:
            raise HTTPException(
                status_code=422,
                detail="Start date must precede end date"
            )


def utc_time(value):
    if value is not None and value.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="Timestamp must include a timezone"
        )
    return value


def response(rows, limit, offset):
    return {
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "data": rows
    }


# 1. HISTORICAL WEATHER

@router.get("/weather/history", tags=["Weather"])
def weather_history(
    commune_code: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    source: str | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    check_dates(start_date, end_date)

    rows = fetch_rows("""
        SELECT w.*, c.nom_fr AS commune_name
        FROM public.weather_daily w
        JOIN public.communes c
            ON c.iso = w.commune_code
        WHERE (%s::text IS NULL OR w.commune_code = %s)
          AND (%s::date IS NULL OR w.observation_date >= %s)
          AND (%s::date IS NULL OR w.observation_date <= %s)
          AND (%s::text IS NULL OR w.source = %s)
        ORDER BY w.observation_date DESC, w.id
        LIMIT %s OFFSET %s
    """, (
        commune_code, commune_code,
        start_date, start_date,
        end_date, end_date,
        source, source,
        limit, offset
    ))

    return response(rows, limit, offset)


# 2. WEATHER FORECASTS

@router.get("/weather/forecasts", tags=["Weather"])
def weather_forecasts(
    commune_code: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    latest_only: bool = True,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    start_time = utc_time(start_time)
    end_time = utc_time(end_time)
    check_dates(start_time, end_time)

    rows = fetch_rows("""
        WITH selected AS (
            SELECT f.*, c.nom_fr AS commune_name,
                MAX(f.retrieved_at) OVER (
                    PARTITION BY f.commune_code,
                                 f.source, f.model
                ) AS latest_retrieval
            FROM public.weather_forecasts f
            JOIN public.communes c
                ON c.iso = f.commune_code
            WHERE (%s::text IS NULL OR f.commune_code = %s)
        )
        SELECT *
        FROM selected
        WHERE (%s::timestamptz IS NULL OR valid_at >= %s)
          AND (%s::timestamptz IS NULL OR valid_at <= %s)
          AND (NOT %s OR retrieved_at = latest_retrieval)
        ORDER BY valid_at, commune_code, id
        LIMIT %s OFFSET %s
    """, (
        commune_code, commune_code,
        start_time, start_time,
        end_time, end_time,
        latest_only,
        limit, offset
    ))

    return response(rows, limit, offset)


# 3. FIRMS FIRE DETECTIONS

@router.get("/fires", tags=["Wildfires"])
def fire_detections(
    commune_code: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    start_time = utc_time(start_time)
    end_time = utc_time(end_time)
    check_dates(start_time, end_time)

    rows = fetch_rows("""
        SELECT
            ST_AsGeoJSON(f.geom)::json AS geometry,
            to_jsonb(f) - 'geom' AS properties
        FROM public.fire_detections f
        WHERE (%s::text IS NULL OR f.commune_code = %s)
          AND (%s::timestamptz IS NULL OR f.detected_at >= %s)
          AND (%s::timestamptz IS NULL OR f.detected_at <= %s)
        ORDER BY f.detected_at DESC, f.id
        LIMIT %s OFFSET %s
    """, (
        commune_code, commune_code,
        start_time, start_time,
        end_time, end_time,
        limit, offset
    ))

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": row["geometry"],
                "properties": row["properties"]
            }
            for row in rows
        ],
        "count": len(rows),
        "limit": limit,
        "offset": offset
    }


# 4. HISTORICAL AND FORECAST HAZARD ASSESSMENTS

@router.get("/hazards", tags=["Hazards"])
def hazard_assessments(
    commune_code: str | None = None,
    hazard_type: HazardType | None = None,
    assessment_type: AssessmentType | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    start_time = utc_time(start_time)
    end_time = utc_time(end_time)
    check_dates(start_time, end_time)

    rows = fetch_rows("""
        SELECT h.*, c.nom_fr AS commune_name
        FROM public.hazard_assessments h
        JOIN public.communes c
            ON c.iso = h.commune_code
        WHERE (%s::text IS NULL OR h.commune_code = %s)
          AND (%s::text IS NULL OR h.hazard_type = %s)
          AND (%s::text IS NULL OR h.assessment_type = %s)
          AND (%s::timestamptz IS NULL OR h.valid_from >= %s)
          AND (%s::timestamptz IS NULL OR h.valid_from <= %s)
        ORDER BY h.valid_from DESC, h.id
        LIMIT %s OFFSET %s
    """, (
        commune_code, commune_code,
        hazard_type, hazard_type,
        assessment_type, assessment_type,
        start_time, start_time,
        end_time, end_time,
        limit, offset
    ))

    return response(rows, limit, offset)


# 5. LATEST APPLICABLE HAZARD ASSESSMENTS

@router.get("/hazards/latest", tags=["Hazards"])
def latest_hazards(
    commune_code: str | None = None,
    hazard_type: HazardType | None = None,
    assessment_type: AssessmentType = "current",
    at: datetime | None = None
):
    at = utc_time(at) or datetime.now(timezone.utc)

    rows = fetch_rows("""
        SELECT DISTINCT ON (
            h.commune_code,
            h.hazard_type,
            h.model_name,
            h.model_version
        )
            h.*, c.nom_fr AS commune_name
        FROM public.hazard_assessments h
        JOIN public.communes c
            ON c.iso = h.commune_code
        WHERE (%s::text IS NULL OR h.commune_code = %s)
          AND (%s::text IS NULL OR h.hazard_type = %s)
          AND h.assessment_type = %s
          AND h.valid_from <= %s
          AND (h.valid_until IS NULL OR h.valid_until > %s)
          AND h.generated_at <= %s
        ORDER BY
            h.commune_code,
            h.hazard_type,
            h.model_name,
            h.model_version,
            h.generated_at DESC,
            h.valid_from DESC,
            h.id DESC
    """, (
        commune_code, commune_code,
        hazard_type, hazard_type,
        assessment_type,
        at, at, at
    ))

    return {
        "count": len(rows),
        "as_of": at,
        "data": rows
    }


# 6. HAZARD ALERTS

@router.get("/alerts", tags=["Alerts"])
def hazard_alerts(
    commune_code: str | None = None,
    hazard_type: HazardType | None = None,
    status: Literal[
        "active", "resolved", "expired"
    ] | None = None,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    rows = fetch_rows("""
        WITH alerts AS (
            SELECT
                a.*,
                h.commune_code,
                h.hazard_type,
                h.risk_score,
                h.risk_level,
                h.validation_status,
                c.nom_fr AS commune_name,
                CASE
                    WHEN a.status = 'active'
                         AND a.expires_at <= NOW()
                    THEN 'expired'
                    ELSE a.status
                END AS effective_status
            FROM public.hazard_alerts a
            JOIN public.hazard_assessments h
                ON h.id = a.assessment_id
            JOIN public.communes c
                ON c.iso = h.commune_code
        )
        SELECT *
        FROM alerts
        WHERE (%s::text IS NULL OR commune_code = %s)
          AND (%s::text IS NULL OR hazard_type = %s)
          AND (%s::text IS NULL OR effective_status = %s)
        ORDER BY issued_at DESC, id DESC
        LIMIT %s OFFSET %s
    """, (
        commune_code, commune_code,
        hazard_type, hazard_type,
        status, status,
        limit, offset
    ))

    return response(rows, limit, offset)
