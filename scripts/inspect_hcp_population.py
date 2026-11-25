import pandas as pd
import unicodedata
from pathlib import Path

path = (
    Path.home() / "Downloads" /
    "Population légale du Royaume du Maroc selon les résultats du RGPH 2024, format EXCEL.xlsx"
)

df = pd.read_excel(
    path,
    sheet_name="Population_légale",
    header=None,
    skiprows=7,
    usecols="A:G"
)

df.columns = [
    "name_fr",
    "moroccans",
    "foreigners",
    "population",
    "households",
    "name_ar",
    "geo_code",
]

def normalize(value):
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(
        char for char in text
        if not unicodedata.combining(char)
    ).lower()

terms = [
    "tanger",
    "assilah",
    "asilah",
    "briech",
    "azzinate",
    "manzla",
    "chaoui",
    "souani",
    "aaouama",
    "aouama",
    "ennhal",
    "gueznaia",
    "makada",
    "medina",
    "mghogha",
]

print("=== HCP RGPH 2024 — TERRALERT MATCHES ===")

for term in terms:
    matches = df[
        df["name_fr"].apply(
            lambda value: term in normalize(value)
        )
    ]

    print(f"\n--- {term.upper()} ---")

    if matches.empty:
        print("No direct name match")
        continue

    print(
        matches[
            ["name_fr", "population", "geo_code"]
        ].to_string(index=False)
    )

print("\n=== DATASET INFORMATION ===")
print("Total rows:", len(df))
print("Rows with population:", df["population"].notna().sum())
