"""Automated tests for TERRALERT optional LLM providers."""

import os
import unittest
from unittest.mock import patch

from ai_assistant.llm_adapter import generate
from ai_assistant.hosted_llm import (
    generate_hosted,
    HostedLLMError,
)


QUESTION = "How are heatwaves detected?"
EVIDENCE = "Heatwaves exceed monthly P90 for 3 consecutive days."

HOSTED_REPLY = {
    "mode": "HOSTED_LLM",
    "answer": "Heatwaves are identified using the P90 criterion.",
    "llm_used": True,
    "model": "mock-model",
    "verification_required": True,
}


class TestLLMProviders(unittest.TestCase):

    def test_disabled_ai_makes_no_hosted_call(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "0",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted"
            ) as mocked:
                result = generate(QUESTION, EVIDENCE)

            mocked.assert_not_called()
            self.assertFalse(result["llm_used"])
            self.assertEqual(result["answer"], EVIDENCE)

    def test_hosted_provider_mock(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted",
                return_value=HOSTED_REPLY,
            ) as mocked:
                result = generate(QUESTION, EVIDENCE)

        mocked.assert_called_once_with(QUESTION, EVIDENCE)
        self.assertEqual(result["mode"], "HOSTED_LLM")
        self.assertTrue(result["llm_used"])

    def test_hosted_failure_fallback(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "hosted",
        }):
            with patch(
                "ai_assistant.llm_adapter.generate_hosted",
                side_effect=HostedLLMError("Simulated outage"),
            ):
                result = generate(QUESTION, EVIDENCE)

        self.assertEqual(result["mode"], "RETRIEVAL_ONLY")
        self.assertEqual(result["answer"], EVIDENCE)

    def test_unknown_provider(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "1",
            "TERRALERT_LLM_PROVIDER": "unknown",
        }):
            result = generate(QUESTION, EVIDENCE)

        self.assertFalse(result["llm_used"])

    def test_missing_hosted_credentials(self):
        with patch.dict(os.environ, {
            "TERRALERT_OPENAI_API_KEY": "",
            "TERRALERT_OPENAI_MODEL": "",
        }):
            with self.assertRaises(HostedLLMError):
                generate_hosted(QUESTION, EVIDENCE)

    def test_hosted_empty_evidence(self):
        with patch.dict(os.environ, {
            "TERRALERT_OPENAI_API_KEY": "mock-key",
            "TERRALERT_OPENAI_MODEL": "mock-model",
        }):
            with self.assertRaises(HostedLLMError):
                generate_hosted(QUESTION, "")

    def test_no_llm_without_opt_in(self):
        with patch.dict(os.environ, {
            "TERRALERT_LLM_ENABLED": "0",
            "TERRALERT_LLM_PROVIDER": "ollama",
            "TERRALERT_LLM_MODEL": "mock-model",
        }):
            with patch(
                "ai_assistant.llm_adapter.urlopen"
            ) as mocked:
                result = generate(QUESTION, EVIDENCE)

            mocked.assert_not_called()
            self.assertFalse(result["llm_used"])


if __name__ == "__main__":
    unittest.main()
