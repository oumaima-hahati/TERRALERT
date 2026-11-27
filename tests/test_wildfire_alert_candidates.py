import unittest
from scripts.generate_wildfire_alert_candidates import assess, level_from_fwi

class WildfireAlertCandidateTests(unittest.TestCase):
    def row(self, value, commune='Gueznaia', day='2026-11-28'):
        return {'commune': commune, 'date': day, 'fwi': str(value), 'danger_level': level_from_fwi(value), 'quality': 'provisional', 'model_status': 'PROVISIONAL_RESEARCH', 'weather_source': 'Open-Meteo', 'forecast_run':'20261127T174202Z'}

    def test_low_generates_no_alert(self):
        self.assertEqual(assess([self.row(8.217)], '2026-11-27T17:00:00+00:00'), [])

    def test_high_generates_candidate(self):
        a=assess([self.row(25)], '2026-11-27T17:00:00+00:00')
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]['status'],'RESEARCH_ONLY_NOT_ISSUED')
        self.assertEqual(a[0]['danger_level'],'High')

    def test_boundary_levels(self):
        self.assertEqual([level_from_fwi(x) for x in [5.199,5.2,11.2,21.3,38,50]], ['Very Low','Low','Moderate','High','Very High','Extreme'])

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            assess([self.row(25), self.row(25)], 'x')

    def test_mismatch_rejected(self):
        r=self.row(8.2);r['danger_level']='Extreme'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            assess([r], 'x')

    def test_nan_rejected(self):
        r=self.row(25);r['fwi']='NaN'
        with self.assertRaisesRegex(ValueError, 'invalid FWI'):
            assess([r], 'x')

    def test_mixed_runs_rejected(self):
        r1=self.row(25)
        r2=self.row(39, commune='Souani');r2['forecast_run']='other'
        with self.assertRaisesRegex(ValueError,'Mixed forecast runs'):
            assess([r1,r2], 'x')

if __name__ == '__main__':unittest.main()
