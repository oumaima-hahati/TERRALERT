import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'forecast_thermal_extremes.py'
spec = importlib.util.spec_from_file_location('thermal_leadtime', MODULE_PATH)
thermal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thermal)


class LeadTimeTests(unittest.TestCase):
    def classify(self, start, end, issued='2026-11-27T10:24:34+00:00'):
        ev = [{'commune': 'Aquouass Briech', 'hazard': 'coldwave',
               'start_date_utc': start, 'end_date_utc': end,
               'duration_days': 3, 'status': 'PROVISIONAL_RESEARCH'}]
        return thermal.classify_forecast_lead_time(ev, issued)[0]

    def test_today_plus_three_future_days(self):
        event = self.classify('2026-11-27', '2026-11-30')
        self.assertEqual(event['prospective_assessment'], 'CURRENT_DAY_INCLUDED_FUTURE_RUN_CONFIRMED')
        self.assertEqual(event['fully_future_consecutive_days'], 3)
        self.assertEqual(event['prospective_event_start_date_utc'], '2026-11-28')
        self.assertTrue(event['prospective_three_day_run'])

    def test_today_plus_two_future_days_not_sufficient(self):
        event = self.classify('2026-11-27', '2026-11-29')
        self.assertEqual(event['prospective_assessment'], 'CURRENT_DAY_DEPENDENT_INSUFFICIENT_FUTURE_DAYS')
        self.assertEqual(event['fully_future_consecutive_days'], 2)
        self.assertFalse(event['prospective_three_day_run'])

    def test_fully_future_event(self):
        event = self.classify('2026-11-28', '2026-11-30')
        self.assertEqual(event['prospective_assessment'], 'UPCOMING_FULLY_FUTURE')
        self.assertEqual(event['prospective_event_start_date_utc'], '2026-11-28')

    def test_no_future_days(self):
        event = self.classify('2026-11-24', '2026-11-27')
        self.assertEqual(event['prospective_assessment'], 'NO_FULLY_FUTURE_DAYS')
        self.assertEqual(event['fully_future_consecutive_days'], 0)

    def test_invalid_retrieval_timezone(self):
        with self.assertRaisesRegex(ValueError, 'timezone-aware UTC'):
            self.classify('2026-11-27', '2026-11-30', '2026-11-27T10:24:34')
