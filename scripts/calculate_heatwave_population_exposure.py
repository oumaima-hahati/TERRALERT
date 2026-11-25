#!/usr/bin/env python3
"""HCP RGPH 2024 population reference for historical heatwaves."""

from pathlib import Path
import pandas as pd

HCP = (
    Path.home() / "Downloads" /
    "Population légale du Royaume du Maroc selon les résultats du RGPH 2024, format EXCEL.xlsx"
)
EVENTS = Path(
    "data/heatwaves/processed/heatwave_events_2001_2025.csv"
)
OUT = Path("data/heatwaves/processed")
OUT.mkdir(parents=True, exist_ok=True)

# TERRALERT name -> (official HCP name, geographic code)
mapping = {
    "Aquouass Briech": ("Commune d'Aquouass Briech", "15110303"),
    "Sebt Azzinate": ("Commune de Sebt Azzinate", "15110505"),
    "Al Manzla": ("Commune d'Al Manzla", "15110501"),
    "Dar Chaoui": ("Commune de Dar Chaoui", "15110507"),
    "Souani": ("Arrondissement de Souani", "15110106"),
    "Laaouama": ("Commune de Laaouama", "15110517"),
    "Hjar Ennhal": ("Commune de Hjar Ennhal", "15110519"),
    "Gueznaia": ("Commune de Gueznaia", "15110109"),
    "Bni Makada": ("Arrondissement de Bni Makada", "15110103"),
    "Médina": ("Arrondissement de Médina", "15110107"),
    "Mghogha": ("Arrondissement de Mghogha", "15110105"),
}

hcp = pd.read_excel(
    HCP, sheet_name="Population_légale",
    header=None, skiprows=7, usecols="A:G"
)
hcp.columns = [
    "name_fr", "moroccans", "foreigners",
    "population", "households", "name_ar", "geo_code"
]

hcp["geo_code"] = pd.to_numeric(
    hcp["geo_code"], errors="coerce"
).astype("Int64").astype("string")

population_rows = []

for commune, (official_name, code) in mapping.items():
    match = hcp[
        (hcp["name_fr"] == official_name)
        & (hcp["geo_code"] == code)
    ]

    if len(match) != 1:
        raise ValueError(
            f"{commune}: expected one matching HCP record, "
            f"found {len(match)}"
        )

    row = match.iloc[0]
    pop = int(row["population"])

    if pop <= 0:
        raise ValueError(f"Invalid population for {commune}")

    population_rows.append({
        "commune": commune,
        "official_hcp_name": official_name,
        "hcp_geo_code": code,
        "population_2024": pop,
        "households_2024": int(row["households"]),
        "population_source": "HCP_RGPH_2024",
    })

population = pd.DataFrame(population_rows)

events = pd.read_csv(EVENTS)

if not set(events["commune"]).issubset(set(population["commune"])):
    raise ValueError("Heatwave communes do not match population")

if events["heatwave_id"].duplicated().any():
    raise ValueError("Duplicate heatwave IDs")

events["duration_days"] = pd.to_numeric(
    events["duration_days"], errors="raise"
).astype(int)

if (events["duration_days"] < 3).any():
    raise ValueError("Unexpected heatwave duration")

exposure = events.merge(
    population[
        ["commune", "hcp_geo_code", "population_2024"]
    ],
    on="commune",
    how="left",
    validate="many_to_one"
)

if exposure["population_2024"].isna().any():
    raise ValueError("Missing population after merge")

# Scenario: everyone in a flagged administrative area
# is counted as potentially exposed.
exposure["potential_exposed_people_2024"] = (
    exposure["population_2024"]
)
exposure["potential_person_days_2024"] = (
    exposure["population_2024"] * exposure["duration_days"]
)
exposure["exposure_method"] = (
    "Area-wide potential exposure; 2024 population reference"
)

summary = exposure.groupby("commune", as_index=False).agg(
    heatwave_events=("heatwave_id", "count"),
    heatwave_days=("duration_days", "sum"),
    potential_person_days_2024=("potential_person_days_2024", "sum"),
)

summary = population.merge(
    summary, on="commune", how="left",
    validate="one_to_one"
)

summary["heatwave_events"] = (
    summary["heatwave_events"].fillna(0).astype(int)
)
summary["heatwave_days"] = (
    summary["heatwave_days"].fillna(0).astype(int)
)
summary["potential_person_days_2024"] = (
    summary["potential_person_days_2024"].fillna(0).astype("int64")
)

population.to_csv(
    OUT / "population_rgph2024_11_communes.csv", index=False
)
exposure.to_csv(
    OUT / "heatwave_population_exposure.csv", index=False
)
summary.to_csv(
    OUT / "heatwave_population_exposure_summary.csv", index=False
)

print("=== TERRALERT HEATWAVE POPULATION EXPOSURE ===")
print("HCP administrative areas:", len(population))
print("2024 reference population:", population["population_2024"].sum())
print("Historical heatwave events:", len(exposure))
print("Historical commune-days:", int(exposure["duration_days"].sum()))
print("\n=== COMMUNE EXPOSURE SUMMARY ===")
print(summary[
    ["commune", "population_2024", "heatwave_events",
     "potential_person_days_2024"]
].to_string(index=False))
print("\nSUCCESS: Population exposure datasets generated!")
print("NOTE: Historical potential exposure using 2024 population.")
print("NOT observed health impact or historical population estimates.")
