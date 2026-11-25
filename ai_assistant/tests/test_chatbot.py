"""Regression tests for the TERRALERT GIS assistant."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_assistant.standalone import app
from ai_assistant.retrieval import search
from ai_assistant.llm_adapter import generate


class TestGISAssistant(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def ask(self, question):
        response = self.client.post(
            "/chatbot/ask",
            json={"question": question},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_rainfall_query(self):
        result = self.ask("Rainfall Gueznaia 72h")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["mode"], "STRUCTURED_DATA")
        self.assertEqual(result["data"]["horizon_hours"], 72)
        self.assertGreaterEqual(
            result["data"]["rainfall_total_mm"], 0
        )
        self.assertTrue(result["sources"])

    def test_wildfire_query(self):
        result = self.ask("Wildfire Al Manzla")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertGreaterEqual(result["data"]["fwi"], 0)
        self.assertIn("forecast_date", result["data"])
        self.assertIn("forecast_expired", result["data"])
        self.assertIn("not an official warning", result["answer"])

    def test_heatwave_historical_data(self):
        result = self.ask("Heatwave Aquouass Briech")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertGreater(
            result["data"]["historical_heatwave_events"], 0
        )
        self.assertIn("not observed", result["answer"])

    def test_coldwave_historical_data(self):
        result = self.ask("Coldwave Aquouass Briech")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertGreater(
            result["data"]["historical_coldwave_events"], 0
        )

    def test_scientific_retrieval(self):
        with patch.dict(
            os.environ, {"TERRALERT_LLM_ENABLED": "0"}
        ):
            result = self.ask("How are heatwaves detected?")
        self.assertEqual(result["mode"], "DOCUMENT_RETRIEVAL")
        self.assertFalse(result["llm_used"])
        self.assertTrue(result["sources"])
        self.assertIn(
            "WEATHER_EXTREMES_QA.md",
            result["sources"][0]["file"],
        )

    def test_coldwave_terminology(self):
        for question in (
            "How are coldwaves detected?",
            "How are cold waves detected?",
        ):
            results = search(question)
            self.assertTrue(results)
            self.assertIn(
                "WEATHER_EXTREMES_QA.md",
                results[0]["source"],
            )

    def test_unsupported_question(self):
        result = self.ask("Population of Casablanca")
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_empty_question(self):
        response = self.client.post(
            "/chatbot/ask",
            json={"question": ""},
        )
        self.assertEqual(response.status_code, 422)

    def test_llm_disabled_fallback(self):
        with patch.dict(
            os.environ, {"TERRALERT_LLM_ENABLED": "0"}
        ):
            result = generate(
                "Explain wildfire risk",
                "Evidence supplied by TERRALERT",
            )
        self.assertFalse(result["llm_used"])
        self.assertEqual(result["mode"], "RETRIEVAL_ONLY")


if __name__ == "__main__":
    unittest.main()
