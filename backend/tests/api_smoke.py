import json
import os
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError

BASE = os.getenv(
    "TERRALERT_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


def request(path):
    try:
        with urlopen(BASE + path, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


class TestTerralertAPI(unittest.TestCase):

    def test_health(self):
        status, body = request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_database(self):
        status, body = request("/api/db-health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("postgis_version", body)

    def test_gis_layers(self):
        layers = {
            "/api/communes": 11,
            "/api/rivers": 123,
            "/api/flood/indicators": 11
        }

        for path, count in layers.items():
            with self.subTest(endpoint=path):
                status, body = request(path)
                self.assertEqual(status, 200)
                self.assertEqual(
                    body["type"], "FeatureCollection"
                )
                self.assertEqual(
                    len(body["features"]), count
                )

    def test_paginated_endpoints(self):
        paths = [
            "/api/weather/history",
            "/api/weather/forecasts",
            "/api/hazards",
            "/api/alerts"
        ]

        for path in paths:
            with self.subTest(endpoint=path):
                status, body = request(
                    path + "?limit=1&offset=0"
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["limit"], 1)
                self.assertEqual(body["offset"], 0)
                self.assertEqual(
                    body["count"], len(body["data"])
                )
                self.assertLessEqual(body["count"], 1)

    def test_fires(self):
        status, body = request("/api/fires")
        self.assertEqual(status, 200)
        self.assertEqual(
            body["type"], "FeatureCollection"
        )
        for feature in body["features"]:
            self.assertEqual(
                feature["geometry"]["type"], "Point"
            )

    def test_latest_hazards(self):
        status, body = request("/api/hazards/latest")
        self.assertEqual(status, 200)
        self.assertIn("as_of", body)
        self.assertEqual(
            body["count"], len(body["data"])
        )

    def test_hazard_filters(self):
        for hazard in [
            "flood", "wildfire", "heatwave", "coldwave"
        ]:
            with self.subTest(hazard=hazard):
                status, body = request(
                    "/api/hazards?hazard_type=" + hazard
                )
                self.assertEqual(status, 200)
                for row in body["data"]:
                    self.assertEqual(
                        row["hazard_type"], hazard
                    )

    def test_invalid_parameters(self):
        paths = [
            "/api/hazards?hazard_type=invalid",
            "/api/weather/history?limit=0",
            "/api/alerts?offset=-1",
            "/api/weather/history?"
            "start_date=2026-12-01&end_date=2026-01-01",
            "/api/weather/forecasts?"
            "start_time=2026-11-24T12:00:00"
        ]

        for path in paths:
            with self.subTest(endpoint=path):
                status, _ = request(path)
                self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
