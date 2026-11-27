import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'forecast_thermal_extremes.py'
spec = importlib.util.spec_from_file_location('thermal', MODULE_PATH)
thermal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thermal)


def sample(root, cold_days=(0,1,2), heat_days=()):
    root = Path(root)
    hp, cp, fp = [root / x for x in ('heat.csv', 'cold.csv', 'daily_forecast_test.csv')]
    for path, field, val in [(hp, 'threshold_p90_c', 30), (cp, 'threshold_p10_c', 10)]:
        with path.open('w', newline='') as f:
            wr = csv.DictWriter(f, fieldnames=['commune', 'month', field]); wr.writeheader()
            for i in range(11):
                for m in range(1, 13): wr.writerow({'commune': f'C{i}', 'month':m, field:val})
    with fp.open('w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['commune','forecast_date_utc','temperature_max_c','temperature_min_c','retrieved_at_utc','source']); wr.writeheader()
        for i in range(11):
            for d in range(4):
                wr.writerow({'commune': f'C{i}', 'forecast_date_utc':f'2026-11-{27+d:02d}',
                             'temperature_max_c': 35 if d in heat_days else 20,
                             'temperature_min_c': 5 if d in cold_days else 15,
                             'retrieved_at_utc':'2026-11-27T09:00:00+00:00', 'source':'Open-Meteo Forecast API'})
    return fp, hp, cp


class DailyForecastTests(unittest.TestCase):
    def test_three_cold_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = thermal.evaluate_daily(*sample(tmp))
            self.assertEqual(len(result['events']), 11)
            self.assertTrue(all(x['hazard']=='coldwave' for x in result['events']))
            self.assertEqual(len(result['daily']),44)
    def test_two_cold_days_not_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = thermal.evaluate_daily(*sample(tmp,cold_days=(0,1)))
            self.assertEqual(result['events'], [])
    def test_heat_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = thermal.evaluate_daily(*sample(tmp,cold_days=(),heat_days=(1,2,3)))
            self.assertEqual(len(result['events']),11)
            self.assertTrue(all(x['hazard']=='heatwave' for x in result['events']))
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp,hp,cp=sample(tmp)
            with fp.open('r') as f: lines=f.readlines()
            with fp.open('a') as f: f.write(lines[1])
            with self.assertRaisesRegex(ValueError,'Duplicate'): thermal.evaluate_daily(fp,hp,cp)
    def test_invalid_extrema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp,hp,cp=sample(tmp)
            txt=fp.read_text().replace('20,5,','0,5,',1)
            fp.write_text(txt)
            with self.assertRaisesRegex(ValueError,'Invalid extrema'): thermal.evaluate_daily(fp,hp,cp)

if __name__ == '__main__': unittest.main()
