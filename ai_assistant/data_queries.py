#!/usr/bin/env python3
"""TERRALERT: Grounded queries over local risk datasets."""

import csv
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATASETS = {
    "rainfall": "data/weather/forecasts/aggregated/rainfall_weather_24h_72h_*.csv",
    "wildfire": "data/wildfires/forecasts/fwi_forecast_*.csv",
    "heatwave": "data/heatwaves/processed/heatwave_population_exposure_summary.csv",
    "coldwave": "data/coldwaves/processed/coldwave_elevation_summary.csv",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(
        c for c in value if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def latest_data(pattern):
    files = sorted(ROOT.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Dataset unavailable: {pattern}")

    path = files[-1]

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"Empty dataset: {path}")

    return path, rows


def identify_commune(question, rows):
    normalized = f" {normalize(question)} "
    communes = sorted(
        {row["commune"] for row in rows},
        key=len,
        reverse=True
    )

    matches = [
        commune for commune in communes
        if f" {normalize(commune)} " in normalized
    ]

    return matches[0] if matches else None


def identify_type(question):
    text = normalize(question)

    if any(word in text for word in (
        "rainfall", "rain", "precipitation", "pluie", "pluviometrie"
    )):
        return "rainfall"

    if any(word in text for word in (
        "wildfire", "forest fire", "fwi", "incendie", "feu de foret"
    )):
        return "wildfire"

    if any(word in text for word in (
        "heatwave", "heat wave", "canicule", "vague de chaleur"
    )):
        return "heatwave"

    if any(word in text for word in (
        "coldwave", "cold wave", "vague de froid"
    )):
        return "coldwave"

    return None


def number(value):
    return float(value)


def query(question):
    kind = identify_type(question)

    if kind is None:
        return {
            "status": "UNSUPPORTED",
            "answer": (
                "Please ask about rainfall, wildfire, "
                "heatwaves, or cold waves."
            )
        }

    source, rows = latest_data(DATASETS[kind])
    commune = identify_commune(question, rows)

    if commune is None:
        return {
            "status": "COMMUNE_REQUIRED",
            "answer": "Specify one of the TERRALERT study areas.",
            "available_communes": sorted({
                row["commune"] for row in rows
            })
        }

    selected = [
        row for row in rows if row["commune"] == commune
    ]

    result = {
        "status": "SUCCESS",
        "risk_type": kind,
        "commune": commune,
        "source_file": str(source.relative_to(ROOT)),
    }

    if kind == "rainfall":
        match = re.search(
            r"\b(24|72)\s*(?:h|hours|heures)\b",
            question.lower()
        )

        if not match:
            return {
                "status": "HORIZON_REQUIRED",
                "answer": "Specify 24h or 72h.",
                "commune": commune
            }

        horizon = int(match.group(1))
        matches = [
            row for row in selected
            if int(row["horizon_hours"]) == horizon
        ]

        if len(matches) != 1:
            raise ValueError("Invalid rainfall horizon coverage")

        row = matches[0]

        now = datetime.now(timezone.utc)
        end = datetime.fromisoformat(
            row["window_end_utc"].replace("Z", "+00:00")
        )

        result.update({
            "horizon_hours": horizon,
            "rainfall_total_mm": number(row["rainfall_total_mm"]),
            "window_start_utc": row["window_start_utc"],
            "window_end_utc": row["window_end_utc"],
            "retrieved_at_utc": row["retrieved_at_utc"],
            "data_source": row["source"],
            "model_status": row["status"],
            "forecast_expired": end <= now,
        })

        result["answer"] = (
            f"{commune}: {result['rainfall_total_mm']:.2f} mm "
            f"forecast rainfall over {horizon}h, "
            f"from {row['window_start_utc']} "
            f"to {row['window_end_utc']} (UTC). "
            f"Source: {row['source']}. "
            f"{'EXPIRED FORECAST — not current.' if end <= now else 'Provisional research forecast.'}"
        )

    elif kind == "wildfire":
        row = max(selected, key=lambda r: r["date"])

        result.update({
            "forecast_date": row["date"],
            "fwi": number(row["fwi"]),
            "danger_level": row["danger_level"],
            "model_status": row["model_status"],
            "weather_source": row["weather_source"],
            "forecast_run": row["forecast_run"],
            "forecast_expired": (
                row["date"] < datetime.now(timezone.utc)
                .date().isoformat()
            ),
        })

        result["answer"] = (
            f"{commune}: FWI {result['fwi']:.2f}, "
            f"danger category {row['danger_level']} "
            f"on {row['date']}. "
            + (
                "EXPIRED FORECAST — not current. "
                if result["forecast_expired"]
                else "Forecast date has not passed. "
            )
            + "Research-only forecast; not an official warning."
        )

    elif kind == "heatwave":
        row = selected[0]

        result.update({
            "historical_heatwave_events": int(row["heatwave_events"]),
            "historical_heatwave_days": int(row["heatwave_days"]),
            "population_2024": int(row["population_2024"]),
            "potential_person_days_2024": int(
                row["potential_person_days_2024"]
            ),
        })

        result["answer"] = (
            f"{commune}: {row['heatwave_events']} historical "
            f"commune-level heatwave episodes and "
            f"{row['heatwave_days']} heatwave days (2001–2025). "
            f"2024 population: {row['population_2024']}. "
            "Potential exposure is a retrospective estimate "
            "using the fixed 2024 population, not observed "
            "people affected."
        )

    elif kind == "coldwave":
        row = selected[0]

        result.update({
            "historical_coldwave_events": int(row["coldwave_events"]),
            "historical_coldwave_days": int(row["coldwave_days"]),
            "elevation_mean_m": number(row["elevation_mean_m"]),
            "dem_coverage_pct": number(row["dem_coverage_pct"]),
        })

        result["answer"] = (
            f"{commune}: {row['coldwave_events']} historical "
            f"commune-level cold-wave episodes and "
            f"{row['coldwave_days']} cold-wave days (2001–2025). "
            f"Mean terrain elevation: "
            f"{result['elevation_mean_m']:.2f} m. "
            "These are historical research indicators."
        )

    return result


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        raise SystemExit(
            'Usage: python ai_assistant/data_queries.py "question"'
        )

    try:
        result = query(question)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        result = {
            "status": "DATA_ERROR",
            "answer": str(exc)
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
