from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from extractor import extract

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"
GROUND_TRUTH_PATH = ROOT / "ground_truth.jsonl"
RESULTS_PATH = ROOT / "results.csv"
REPORT_PATH = ROOT / "quality_report.md"
CACHE_DIR = ROOT / "cache"
FIELD_NAMES = ["full_name", "father_name", "pan_number", "date_of_birth"]
CONFIGS = ["raw", "rotate", "brightness", "rotate+brightness"]


def normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).upper().replace("'", "")
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_pan(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value).upper())


def normalize_dob(value: str | None) -> str:
    if value is None:
        return ""
    text = re.sub(r"[^0-9/]", "", str(value))
    return text


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            insertions = current[j - 1] + 1
            deletions = previous[j] + 1
            substitutions = previous[j - 1] + (ca != cb)
            current.append(min(insertions, deletions, substitutions))
        previous = current
    return previous[-1]


def value_matches(expected: str | None, actual: str | None, field: str) -> bool:
    if actual is None:
        return False
    if field in {"full_name", "father_name"}:
        return normalize_name(expected) == normalize_name(actual)
    if field == "pan_number":
        return normalize_pan(expected) == normalize_pan(actual)
    if field == "date_of_birth":
        return normalize_dob(expected) == normalize_dob(actual)
    return str(expected).strip() == str(actual).strip()


def _step_set(config: str) -> frozenset[str]:
    if config == "raw":
        return frozenset()
    if config == "rotate":
        return frozenset({"rotate"})
    if config == "brightness":
        return frozenset({"brightness"})
    if config == "rotate+brightness":
        return frozenset({"rotate", "brightness"})
    return frozenset()


def read_ground_truth() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with GROUND_TRUTH_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            record = json.loads(line)
            rows[record["sample_id"]] = record
    return rows


def cache_path(sample_id: str, config: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{sample_id}_{config}.json"


def load_or_run_extraction(sample: dict, config: str) -> dict:
    key_path = cache_path(sample["sample_id"], config)
    if key_path.exists():
        with key_path.open("r", encoding="utf-8") as fp:
            cached = json.load(fp)
        return cached

    image_file = SAMPLES_DIR / sample["image_file"]
    result = extract(image_file, steps=_step_set(config))
    payload = {
        "sample_id": sample["sample_id"],
        "config": config,
        "extraction": result["extraction"].model_dump() if result["extraction"] else None,
        "error": result["error"],
        "latency_s": result["latency_s"],
        "steps_applied": result["steps_applied"],
        "raw_response": getattr(result["raw_response"], "text", None) or str(result["raw_response"]),
    }
    with key_path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    return payload



def compute_metrics_for_result(expected: dict, extraction_payload: dict | None) -> tuple[dict, list[dict]]:
    if extraction_payload is None or extraction_payload.get("extraction") is None:
        return {
            "fields_extracted": 0,
            "fields_correct": 0,
            "fields_wrong": 0,
            "fields_missed": 4,
            "confidence": 0.0,
            "pan_format_valid": False,
            "latency_s": extraction_payload.get("latency_s", 0.0) if extraction_payload else 0.0,
        }, [{"field": field, "expected": expected.get(field), "got": None, "status": "missed"} for field in FIELD_NAMES]

    extraction = extraction_payload["extraction"]
    confidence = float(extraction.get("confidence", 0.0))
    status_rows: list[dict] = []
    correct = 0
    wrong = 0
    missed = 0
    extracted = 0

    for field in FIELD_NAMES:
        got = extraction.get(field)
        if got is None:
            missed += 1
            status_rows.append({"field": field, "expected": expected.get(field), "got": None, "status": "missed"})
            continue

        extracted += 1
        actual = str(got)
        exp = expected.get(field)
        if value_matches(exp, actual, field):
            correct += 1
            status_rows.append({"field": field, "expected": exp, "got": actual, "status": "correct"})
        else:
            wrong += 1
            status_rows.append({"field": field, "expected": exp, "got": actual, "status": "wrong"})

    return {
        "fields_extracted": extracted,
        "fields_correct": correct,
        "fields_wrong": wrong,
        "fields_missed": missed,
        "confidence": confidence,
        "pan_format_valid": bool(extraction.get("pan_format_valid", False)),
        "latency_s": extraction_payload.get("latency_s", 0.0),
    }, status_rows


def paint_summary(results: list[dict]) -> tuple[dict, dict, dict, list[dict]]:
    quality_summary: dict[str, dict[str, float]] = defaultdict(dict)
    best_configs: dict[str, str] = {}
    failures: list[dict] = []
    confidence_records: list[tuple[float, int]] = []

    for result in results:
        sample = result["sample"]
        quality = sample["image_quality"]
        config = result["config"]
        metrics = result["metrics"]
        total_fields = 4
        accuracy = metrics["fields_correct"] / total_fields if total_fields else 0.0
        quality_summary.setdefault(quality, {})[config] = accuracy

        if metrics["fields_correct"] == 4:
            confidence_records.append((metrics["confidence"], 1))
        else:
            confidence_records.append((metrics["confidence"], 0))

        for detail in result["status_rows"]:
            if detail["status"] != "correct":
                failures.append({
                    "sample_id": sample["sample_id"],
                    "image_quality": quality,
                    "config": config,
                    "field": detail["field"],
                    "expected": detail["expected"],
                    "got": detail["got"],
                    "status": detail["status"],
                })

    # Best config per image-quality bucket, relative to raw baseline.
    best_configs = {}
    for quality, scores in quality_summary.items():
        raw_acc = scores.get("raw", 0.0)
        best_config = max(scores, key=lambda key: (scores[key] - raw_acc if key != "raw" else -1e9, scores[key]))
        best_configs[quality] = best_config

    calibration = {
        "all_correct_mean_confidence": 0.0,
        "any_error_mean_confidence": 0.0,
        "correct_count": 0,
        "error_count": 0,
    }
    all_conf_correct = []
    all_conf_error = []
    for result in results:
        metrics = result["metrics"]
        if metrics["fields_correct"] == 4:
            all_conf_correct.append(metrics["confidence"])
        else:
            all_conf_error.append(metrics["confidence"])
    if all_conf_correct:
        calibration["all_correct_mean_confidence"] = sum(all_conf_correct) / len(all_conf_correct)
    if all_conf_error:
        calibration["any_error_mean_confidence"] = sum(all_conf_error) / len(all_conf_error)
    calibration["correct_count"] = len(all_conf_correct)
    calibration["error_count"] = len(all_conf_error)

    return quality_summary, best_configs, calibration, failures


def generate_report(rows: list[dict], quality_summary: dict, best_configs: dict, calibration: dict, failures: list[dict]) -> None:
    report_lines = [
        "# PAN Card Extraction Quality Report",
        "",
        "This report is generated from the actual evaluation run and includes dummy-only PAN card samples.",
        "",
        "## Accuracy by image quality and config",
        "",
        "| image_quality | raw | rotate | brightness | rotate+brightness |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for quality in sorted(quality_summary):
        values = quality_summary[quality]
        row = [quality]
        for config in ["raw", "rotate", "brightness", "rotate+brightness"]:
            row.append(f"{values.get(config, 0.0):.3f}")
        report_lines.append(f"| {' | '.join(row)} |")

    report_lines.extend([
        "",
        "## Best config per quality bucket",
        "",
        "| image_quality | best_config | delta_vs_raw |",
        "| --- | --- | ---: |",
    ])

    for quality in sorted(best_configs):
        raw_acc = quality_summary[quality].get("raw", 0.0)
        best_conf = best_configs[quality]
        delta = quality_summary[quality].get(best_conf, 0.0) - raw_acc
        report_lines.append(f"| {quality} | {best_conf} | {delta:.3f} |")

    report_lines.extend([
        "",
        "## Confidence calibration",
        "",
        f"- Mean confidence when all fields correct: {calibration['all_correct_mean_confidence']:.3f}",
        f"- Mean confidence when any field wrong or missed: {calibration['any_error_mean_confidence']:.3f}",
        "",
        "## Failure list",
        "",
        "| sample_id | image_quality | config | field | expected | got | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])

    if not failures:
        report_lines.append("| — | — | — | — | — | — | — |")
    else:
        for failure in failures:
            report_lines.append(
                f"| {failure['sample_id']} | {failure['image_quality']} | {failure['config']} | {failure['field']} | {failure['expected']} | {failure['got']} | {failure['status']} |"
            )

    report_lines.extend([
        "",
        "## Analysis (fill in manually)",
        "",
        "### What preprocessing helped or hurt",
        "",
        "- Fill in with the observed effect of rotate, brightness, and combined preprocessing for each image-quality bucket.",
        "",
        "### Where the model still fails",
        "",
        "- Fill in with examples of OCR errors, partial-card issues, or inconsistent field extraction.",
        "",
        "### Caveats",
        "",
        "- Tiny sample size: this study uses a small set of synthetic PAN-card samples.",
        "- Single document template: the cards are all generated from the same style and layout.",
        "- Dummy data only: the card text is synthetic and not tied to real individuals.",
    ])

    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def run_evaluation() -> None:
    load_dotenv()
    rows = read_ground_truth()
    all_results = []

    for sample_id in tqdm(sorted(rows), desc="Evaluating PAN samples"):
        sample = rows[sample_id]
        image_path = SAMPLES_DIR / sample["image_file"]
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image for sample: {image_path}")

        for config in CONFIGS:
            payload = load_or_run_extraction(sample, config)
            metrics, status_rows = compute_metrics_for_result(sample["expected"], payload)
            all_results.append({
                "sample": sample,
                "config": config,
                "metrics": metrics,
                "status_rows": status_rows,
            })

    quality_summary, best_configs, calibration, failures = paint_summary(all_results)
    generate_report(all_results, quality_summary, best_configs, calibration, failures)

    output_rows = []
    for result in all_results:
        sample = result["sample"]
        metrics = result["metrics"]
        output_rows.append({
            "sample_id": sample["sample_id"],
            "image_quality": sample["image_quality"],
            "config": result["config"],
            "fields_extracted": metrics["fields_extracted"],
            "fields_correct": metrics["fields_correct"],
            "fields_wrong": metrics["fields_wrong"],
            "fields_missed": metrics["fields_missed"],
            "confidence": metrics["confidence"],
            "pan_format_valid": metrics["pan_format_valid"],
            "latency_s": metrics["latency_s"],
        })

    pd.DataFrame(output_rows).to_csv(RESULTS_PATH, index=False)

    print(f"Saved {len(output_rows)} evaluation rows to {RESULTS_PATH}")
    print(f"Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    run_evaluation()
