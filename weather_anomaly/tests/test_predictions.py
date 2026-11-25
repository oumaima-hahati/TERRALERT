"""Regression tests for TERRALERT weather anomaly outputs."""

import json
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from weather_anomaly.features import (
    FEATURES,
    load_weather,
    prepare_features,
)
from weather_anomaly.predict import predict


LOCAL = Path("weather_anomaly/.local")


class TestWeatherAnomalies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = predict(2024, 2025)
        cls.metadata = json.loads(
            (LOCAL / "model_metadata.json").read_text()
        )
        cls.threshold = float(
            cls.metadata["anomaly_threshold"]
        )

    def test_all_communities_present(self):
        self.assertEqual(
            self.results["commune"].nunique(), 11
        )

    def test_complete_test_period(self):
        self.assertEqual(len(self.results), 8041)
        self.assertEqual(
            self.results.groupby("commune").size().nunique(),
            1,
        )
        self.assertEqual(
            self.results.groupby("commune").size().iloc[0],
            731,
        )

    def test_no_duplicate_commune_dates(self):
        self.assertFalse(
            self.results.duplicated(
                ["commune", "date"]
            ).any()
        )

    def test_no_missing_or_infinite_scores(self):
        scores = self.results["anomaly_score"].to_numpy()
        self.assertTrue(np.isfinite(scores).all())

    def test_flags_match_saved_threshold(self):
        expected = (
            self.results["anomaly_score"]
            <= self.threshold
        )
        np.testing.assert_array_equal(
            self.results["is_anomaly"].to_numpy(),
            expected.to_numpy(),
        )

    def test_model_features_match_metadata(self):
        self.assertEqual(
            self.metadata["features"], FEATURES
        )

    def test_saved_model_reproduces_scores(self):
        model = joblib.load(
            LOCAL / "isolation_forest.joblib"
        )

        weather = load_weather()
        prepared, _ = prepare_features(weather)

        selected = prepared[
            prepared["year"].between(2024, 2025)
        ].sort_values(["date", "commune"])

        X = selected[FEATURES].to_numpy(dtype=float)

        expected_scores = model.score_samples(X)

        np.testing.assert_allclose(
            expected_scores,
            self.results["anomaly_score"].to_numpy(),
            rtol=1e-10,
            atol=1e-10,
        )

    def test_research_label_present(self):
        self.assertTrue(
            (
                self.results["result_type"]
                == "STATISTICAL_ANOMALY_RESEARCH"
            ).all()
        )

    def test_csv_export(self):
        path = LOCAL / "weather_anomalies_2024_2025.csv"

        self.assertTrue(path.exists())

        exported = pd.read_csv(path)
        self.assertEqual(len(exported), len(self.results))


if __name__ == "__main__":
    unittest.main()
