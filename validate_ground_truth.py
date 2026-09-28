from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"
GROUND_TRUTH_PATH = ROOT / "ground_truth.jsonl"


def validate() -> None:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(f"Missing ground-truth file: {GROUND_TRUTH_PATH}")

    truth_records = []
    with GROUND_TRUTH_PATH.open("r", encoding="utf-8") as fp:
        for line_number, line in enumerate(fp, start=1):
            if not line.strip():
                continue
            data = json.loads(line)
            truth_records.append(data)

    truth_by_sample = {record["sample_id"]: record for record in truth_records}
    sample_files = {p.stem: p.name for p in SAMPLES_DIR.iterdir() if p.is_file()}

    missing_from_ground_truth = sorted(set(sample_files) - set(truth_by_sample))
    missing_from_samples = sorted(set(truth_by_sample) - set(sample_files))

    if missing_from_ground_truth or missing_from_samples:
        raise ValueError(
            "Ground-truth mismatch: "
            f"missing_from_ground_truth={missing_from_ground_truth}, "
            f"missing_from_samples={missing_from_samples}"
        )

    print(f"Validated {len(truth_records)} ground-truth rows against {len(sample_files)} sample files.")


if __name__ == "__main__":
    validate()
