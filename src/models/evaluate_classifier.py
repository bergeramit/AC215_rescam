#!/usr/bin/env python3
"""
Compare base Gemini vs fine-tuned Gemini on phishing classification.

Usage:
    python3 evaluate_finetuned_vs_base.py \
        --tuning-job-name projects/1097076476714/locations/us-east1/tuningJobs/XXXXXXXXXXXX \
        --max-examples 200
"""

import argparse
import time

import pandas as pd
from google import genai
from google.genai import types

PROJECT_ID = "1097076476714"
LOCATION = "us-east1"
DEFAULT_BUCKET = "rescam-dataset-bucket"
DEFAULT_PATH = "processed-dataset/cleaned_dataset.parquet"

LABEL_MAPPING = {0: "benign", 1: "scam"}


def make_client():
    return genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION,
        http_options=types.HttpOptions(api_version="v1"),
    )


def download_dataset(bucket: str, path: str, local_path: str) -> pd.DataFrame:
    from google.cloud import storage

    storage_client = storage.Client(project=PROJECT_ID)
    blob = storage_client.bucket(bucket).blob(path)
    if not blob.exists():
        raise FileNotFoundError(f"Dataset not found: gs://{bucket}/{path}")
    blob.download_to_filename(local_path)
    df = pd.read_parquet(local_path)
    if "label" not in df.columns:
        raise ValueError("Dataset must contain a 'label' column")
    return df


def prepare_prompt(subject: str, body: str) -> str:
    email_text = f"Subject: {subject or ''}\n\n{body or ''}".strip()
    return f"""You are a phishing email classifier.

Classify this email as exactly one of: "scam" or "benign".

Email:
{email_text}

Answer with just one word: scam or benign.
"""


def normalize_prediction(text: str) -> str:
    if not text:
        return "unknown"
    lowered = text.lower()
    if "scam" in lowered and "benign" not in lowered:
        return "scam"
    if "benign" in lowered and "scam" not in lowered:
        return "benign"
    if "phishing" in lowered:
        return "scam"
    if "legit" in lowered or "legitimate" in lowered:
        return "benign"
    return "unknown"


def compute_metrics(df_results: pd.DataFrame) -> dict:
    tp = len(df_results[(df_results["label"] == "scam") & (df_results["prediction"] == "scam")])
    tn = len(df_results[(df_results["label"] == "benign") & (df_results["prediction"] == "benign")])
    fp = len(df_results[(df_results["label"] == "benign") & (df_results["prediction"] == "scam")])
    fn = len(df_results[(df_results["label"] == "scam") & (df_results["prediction"] == "benign")])
    unknown = len(df_results[df_results["prediction"] == "unknown"])

    total = len(df_results)
    accuracy = (tp + tn) / total if total else 0
    precision_scam = tp / (tp + fp) if (tp + fp) else 0
    recall_scam = tp / (tp + fn) if (tp + fn) else 0
    f1_scam = (
        2 * (precision_scam * recall_scam) / (precision_scam + recall_scam)
        if (precision_scam + recall_scam) > 0
        else 0
    )

    precision_benign = tn / (tn + fn) if (tn + fn) else 0
    recall_benign = tn / (tn + fp) if (tn + fp) else 0
    f1_benign = (
        2 * (precision_benign * recall_benign) / (precision_benign + recall_benign)
        if (precision_benign + recall_benign) > 0
        else 0
    )

    return {
        "accuracy": round(accuracy, 3),
        "precision_scam": round(precision_scam, 3),
        "recall_scam": round(recall_scam, 3),
        "f1_scam": round(f1_scam, 3),
        "precision_benign": round(precision_benign, 3),
        "recall_benign": round(recall_benign, 3),
        "f1_benign": round(f1_benign, 3),
        "false_positive_rate": round(fp / total, 3) if total else 0,
        "false_negative_rate": round(fn / total, 3) if total else 0,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "unknown_predictions": unknown,
        "num_examples": total,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tuning-job-name", required=True)
    parser.add_argument("--source-bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--source-path", default=DEFAULT_PATH)
    parser.add_argument("--local-path", default="eval_dataset.parquet")
    parser.add_argument("--max-examples", type=int, default=200)
    args = parser.parse_args()

    client = make_client()

    print("=" * 70)
    print(f"Tuning job: {args.tuning_job_name}")
    tuning_job = client.tunings.get(name=args.tuning_job_name)
    tuned_endpoint = tuning_job.tuned_model.endpoint
    print(f"Tuned endpoint: {tuned_endpoint}")
    base_model_id = "gemini-2.0-flash-001"
    print(f"Base model:    {base_model_id}")
    print("=" * 70)

    df = download_dataset(args.source_bucket, args.source_path, args.local_path)
    df = df[df["label"].isin([0, 1])]
    df = df.sample(n=min(args.max_examples, len(df)), random_state=42)

    def run_model(model_name: str):
        results = []
        start = time.time()
        for _, row in df.iterrows():
            prompt = prepare_prompt(row.get("subject", ""), row.get("body", ""))
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                pred = normalize_prediction(resp.text)
            except Exception as exc:
                print(f"⚠️  Error: {exc}")
                pred = "unknown"

            results.append({
                "label": LABEL_MAPPING.get(row["label"], "benign"),
                "prediction": pred,
            })

        elapsed = time.time() - start
        return pd.DataFrame(results), elapsed

    base_results, base_time = run_model(base_model_id)
    tuned_results, tuned_time = run_model(tuned_endpoint)

    base_metrics = compute_metrics(base_results)
    tuned_metrics = compute_metrics(tuned_results)

    print("\n=== Base model metrics ===")
    for k, v in base_metrics.items():
        print(f"- {k}: {v}")
    print(f"latency_total_sec: {round(base_time, 2)}")
    print(f"latency_avg_sec:   {round(base_time / base_metrics['num_examples'], 3)}")

    print("\n=== Fine-tuned model metrics ===")
    for k, v in tuned_metrics.items():
        print(f"- {k}: {v}")
    print(f"latency_total_sec: {round(tuned_time, 2)}")
    print(f"latency_avg_sec:   {round(tuned_time / tuned_metrics['num_examples'], 3)}")


if __name__ == "__main__":
    main()