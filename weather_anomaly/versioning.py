"""Portable model artifact manifest for TERRALERT weather anomaly research."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MODEL_VERSION = "1.0.0"


def sha256_file(path):
    """Compute the content hash of an artifact without loading it into memory."""
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_manifest(model_path, metadata_path, *, model_version=MODEL_VERSION, run_id=None):
    """Create an explicit and auditable version record for saved model files."""
    model_path, metadata_path = Path(model_path), Path(metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    required = {"features", "anomaly_threshold", "score_method"}
    missing = required.difference(metadata)
    if missing:
        raise ValueError(f"Missing metadata fields: {sorted(missing)}")
    return {
        "schema_version": SCHEMA_VERSION,
        "model_version": model_version,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": metadata.get("model", "unknown"),
        "features": metadata["features"],
        "anomaly_threshold": metadata["anomaly_threshold"],
        "score_method": metadata["score_method"],
        "training_period": metadata.get("training_period"),
        "mlflow_run_id": run_id,
        "model_file": model_path.name,
        "metadata_file": metadata_path.name,
        "model_sha256": sha256_file(model_path),
        "metadata_sha256": sha256_file(metadata_path),
    }


def save_manifest(manifest, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def verify_manifest(manifest_path):
    """Reject missing, changed or inconsistent model artifacts."""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported model manifest schema version")
    for filename_key, checksum_key in (
        ("model_file", "model_sha256"),
        ("metadata_file", "metadata_sha256"),
    ):
        filename = manifest[filename_key]
        if Path(filename).name != filename:
            raise ValueError("Manifest artifact path must be a filename")
        artifact = path.parent / filename
        if not artifact.is_file():
            raise FileNotFoundError(f"Missing model artifact: {artifact}")
        if sha256_file(artifact) != manifest[checksum_key]:
            raise ValueError(f"Model artifact integrity check failed: {filename}")
    metadata = json.loads((path.parent / manifest["metadata_file"]).read_text(encoding="utf-8"))
    for name in ("features", "anomaly_threshold", "score_method"):
        if manifest[name] != metadata[name]:
            raise ValueError(f"Manifest/metadata mismatch: {name}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Verify TERRALERT model artifacts")
    parser.add_argument("--manifest", default="weather_anomaly/.local/model_manifest.json")
    args = parser.parse_args()
    result = verify_manifest(args.manifest)
    print(f"PASS: {result['model_version']} ({result['model_sha256'][:12]})")


if __name__ == "__main__":
    main()
