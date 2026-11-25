"""End-to-end FastAPI tests with mocked AI generation."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_assistant.standalone import app
from ai_assistant.hosted_llm import HostedLLMError


class TestLLMEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_hosted_methodology_answer(self):
        mocked = {
            "mode": "HOSTED_LLM",
            "answer": (
                "TERRALERT detects heatwaves using the monthly "
                "90th percentile for at least three consecutive days."
            ),
            "llm_used": True,
            "model": "mock-model",
            "verification_required": True,
        }

        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted",
                return_value=mocked,
            ) as provider:
                response = self.client.post(
                    "/chatbot/ask",
                    json={"question": "How are heatwaves detected?"},
                )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["generation_mode"], "HOSTED_LLM")
        self.assertTrue(result["llm_used"])
        self.assertTrue(result["sources"])
        provider.assert_called_once()

    def test_provider_failure_fallback(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted",
                side_effect=HostedLLMError("Simulated outage"),
            ):
                response = self.client.post(
                    "/chatbot/ask",
                    json={"question": "How are heatwaves detected?"},
                )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        self.assertEqual(
            result["generation_mode"], "RETRIEVAL_ONLY"
        )
        self.assertFalse(result["llm_used"])
        self.assertIn("90th percentile", result["answer"])
        self.assertTrue(result["sources"])

    def test_rainfall_never_calls_llm(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted"
            ) as provider:
                response = self.client.post(
                    "/chatbot/ask",
                    json={"question": "Rainfall Gueznaia 72h"},
                )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        self.assertEqual(result["mode"], "STRUCTURED_DATA")
        self.assertGreaterEqual(
            result["data"]["rainfall_total_mm"], 0
        )
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
