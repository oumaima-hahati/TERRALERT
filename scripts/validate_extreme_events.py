#!/usr/bin/env python3
"""Independent event consistency checks for TERRALERT."""

from pathlib import Path
import json
import pandas as pd

ROOT = Path("data")
weather = pd.read_csv(
    ROOT / "weather/processed/daily_weather_nasa_chirps_2001_2025.csv",
    parse_dates=["date"]
)

checks = {}
duplicate_groups = {}

for kind, folder, variable, percentile, operator in [
    ("heatwave", "heatwaves", "temperature_max_c", 0.90, "gt"),
    ("coldwave", "coldwaves", "temperature_min_c", 0.10, "lt"),
]:
    path = ROOT / folder / "processed"
    daily = pd.read_csv(
        path / f"{kind}_daily_2001_2025.csv",
        parse_dates=["date"]
    )
    events = pd.read_csv(
        path / f"{kind}_events_2001_2025.csv"
    )
    thresholds = pd.read_csv(
        path / f"{kind}_monthly_thresholds_2001_2025.csv"
    )

    threshold_col = (
        "threshold_p90_c" if kind == "heatwave"
        else "threshold_p10_c"
    )

    # Recompute thresholds from original weather data.
    source = weather.copy()
    source["month"] = source["date"].dt.month
    reference = (
        source.groupby(["commune", "month"])[variable]
        .quantile(percentile)
        .reset_index(name="recomputed")
    )

    merged = thresholds.merge(
        reference, on=["commune", "month"],
        validate="one_to_one"
    )

    threshold_ok = (
        len(merged) == 132 and
        (merged[threshold_col] - merged["recomputed"])
        .abs().max() < 0.00001
    )

    # Independently reconstruct runs of consecutive extreme days.
    source = source.merge(
        reference, on=["commune", "month"],
        validate="many_to_one"
    )
    source = source.sort_values(
        ["commune", "date"]
    ).reset_index(drop=True)

    extreme = (
        source[variable].gt(source["recomputed"])
        if operator == "gt"
        else source[variable].lt(source["recomputed"])
    )

    gap = (
        source.groupby("commune")["date"]
        .diff().dt.days.ne(1)
    )
    change = (
        extreme.ne(extreme.shift())
        | source["commune"].ne(source["commune"].shift())
    )

    segments = (gap | change).cumsum()
    run_lengths = extreme.groupby(segments).transform("size")
    expected = extreme & run_lengths.ge(3)

    actual = daily.merge(
        source[["commune", "date"]].assign(
            expected=expected.to_numpy()
        ),
        on=["commune", "date"],
        validate="one_to_one"
    )

    classification_ok = (
        len(actual) == len(source)
        and actual[kind].eq(actual["expected"]).all()
    )

    # Reconstruct event boundaries independently.
    runs = source.loc[expected].copy()
    runs["segment"] = segments[expected].to_numpy()
    reconstructed = {
        (commune, str(part["date"].min().date()),
         str(part["date"].max().date()), len(part))
        for (_, commune), part in runs.groupby(
            ["segment", "commune"]
        )
    }

    reported = {
        (str(r.commune), str(r.start_date),
         str(r.end_date), int(r.duration_days))
        for r in events.itertuples()
    }

    event_ok = reconstructed == reported

    checks[kind] = {
        "thresholds_match": bool(threshold_ok),
        "daily_classifications_match": bool(classification_ok),
        "event_boundaries_match": bool(event_ok),
        "events": len(events),
    }

    # Identify locations sharing exactly the same daily
    # minimum or maximum temperature data.
    matrix = weather.pivot(
        index="date", columns="commune", values=variable
    )
    groups = {}
    for commune in matrix.columns:
        signature = tuple(matrix[commune].to_numpy())
        groups.setdefault(signature, []).append(commune)

    duplicate_groups[kind] = [
        names for names in groups.values() if len(names) > 1
    ]

    print(f"\n=== {kind.upper()} ===")
    for key, value in checks[kind].items():
        print(f"{key}: {value}")
    print("Identical temperature-series groups:")
    for names in duplicate_groups[kind]:
        print(" -", ", ".join(names))

report = {
    "checks": checks,
    "identical_series_groups": duplicate_groups,
    "scope": "Retrospective internal scientific consistency",
}
Path("data/qa").mkdir(parents=True, exist_ok=True)
Path("data/qa/extreme_events_consistency.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

passed = all(
    value for result in checks.values()
    for key, value in result.items()
    if key.endswith("_match")
)

if not passed:
    raise SystemExit("\nFAILED: Review event classifications.")

print("\nSUCCESS: Extreme-event consistency checks passed!")
print("NOTE: Identical series limit spatial independence.")
