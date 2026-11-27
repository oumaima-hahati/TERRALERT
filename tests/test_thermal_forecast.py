"""Offline tests: python -m unittest discover -s tests -p 'test_thermal_forecast.py' -v"""
import csv
import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'forecast_thermal_extremes.py'
spec = importlib.util.spec_from_file_location('thermal', MODULE_PATH)
thermal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thermal)

COMMUNES = [f'Commune {i}' for i in range(11)]


def fixture(folder, hours_per_day=24, hot_days=(0, 1, 2), cold_days=()):
    folder = Path(folder)
    heat, cold, hourly = [folder / n for n in ('heat.csv', 'cold.csv', 'forecast.csv')]
    for path, column, value in [(heat, 'threshold_p90_c', 30), (cold, 'threshold_p10_c', 5)]:
        with path.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['commune', 'month', column]); w.writeheader()
            for c in COMMUNES:
                for m in range(1, 13): w.writerow({'commune': c, 'month': m, column: value})
    with hourly.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['commune', 'forecast_time_utc', 'temperature_c', 'retrieved_at_utc', 'source'])
        w.writeheader()
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        for c in COMMUNES:
            for d in range(4):
                for h in range(hours_per_day):
                    dt = start + timedelta(days=d, hours=h)
                    temp = 35 if d in hot_days else (1 if d in cold_days else 15)
                    w.writerow({'commune': c, 'forecast_time_utc': dt.isoformat(), 'temperature_c': temp,
                                'retrieved_at_utc': '2026-06-30T12:00:00+00:00', 'source': 'Open-Meteo Forecast API'})
    return hourly, heat, cold


class ThermalTests(unittest.TestCase):
    def test_three_hot_days(self):
        with tempfile.TemporaryDirectory() as folder:
            result = thermal.evaluate(*fixture(folder))
            heat = [e for e in result['events'] if e['hazard'] == 'heatwave']
            self.assertEqual(len(heat), 11)
            self.assertTrue(all(e['duration_days'] == 3 for e in heat))
            self.assertEqual(result['metadata']['complete_commune_days'], 44)

    def test_two_days_not_enough(self):
        with tempfile.TemporaryDirectory() as folder:
            result = thermal.evaluate(*fixture(folder, hot_days=(0, 1)))
            self.assertEqual(result['events'], [])

    def test_three_cold_days(self):
        with tempfile.TemporaryDirectory() as folder:
            result = thermal.evaluate(*fixture(folder, hot_days=(), cold_days=(1, 2, 3)))
            self.assertEqual(len(result['events']), 11)
            self.assertTrue(all(e['hazard'] == 'coldwave' for e in result['events']))

    def test_incomplete_days_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            result = thermal.evaluate(*fixture(folder, hours_per_day=23))
            self.assertEqual(result['metadata']['complete_commune_days'], 0)
            self.assertEqual(result['events'], [])


if __name__ == '__main__':
    unittest.main()
