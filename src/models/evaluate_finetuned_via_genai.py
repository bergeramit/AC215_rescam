#!/usr/bin/env python3
"""
Evaluate a fine‑tuned Gemini model via the Vertex Generative AI API.

This script uses the preview `google.genai` client to access a fine‑tuned
Gemini model hosted in Vertex AI. You must have the `google‑genai` package
installed and authenticated via Application Default Credentials.

Usage:
    python3 evaluate_finetuned_via_genai.py \
        --tuning-job-name projects/1097076476714/locations/us-east1/tuningJobs/5730230261199667200 \
        --max-examples 200

Prerequisites:
    pip install google-genai
    pip install google-cloud-storage
    pip install pyarrow
    gcloud auth application-default login
    Set GEMINI_API_KEY in your environment for base model evaluation (if needed).
"""

import argparse
import os
import time
import pandas as pd

from google import genai
from google.genai import types
from google.cloud import storage


PROJECT_ID = "1097076476714"
LOCATION = "us-east1"
LABEL_MAPPING = {0: "benign", 1: "scam"}


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


def download_dataset(bucket: str, path: str, local_path: str) -> pd.DataFrame:
    """Download a Parquet dataset from GCS to local storage."""
    storage_client = storage.Client(project=PROJECT_ID)
    blob = storage_client.bucket(bucket).blob(path)
    if not blob.exists():
        raise FileNotFoundError(f"Dataset not found: gs://{bucket}/{path}")
    blob.download_to_filename(local_path)
    df = pd.read_parquet(local_path)
    if "label" not in df.columns:
        raise ValueError("Dataset must contain a 'label' column")
    return df


def main():
    parser = argparse.ArgumentParser(description="Evaluate a fine‑tuned Gemini model via Vertex Generative AI API")
    parser.add_argument("--tuning-job-name", required=True, help="Vertex tuning job resource name")
    parser.add_argument("--source-bucket", default="rescam-dataset-bucket", help="GCS bucket containing the dataset")
    parser.add_argument("--source-path", default="processed-dataset/cleaned_dataset.parquet", help="Path within GCS bucket")
    parser.add_argument("--local-path", default="eval_dataset.parquet", help="Local filename to cache the dataset")
    parser.add_argument("--max-examples", type=int, default=200, help="Number of samples to evaluate")
    args = parser.parse_args()

    # Initialize the Vertex Generative AI client
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION,
        http_options=types.HttpOptions(api_version="v1"),
    )

    # Retrieve the tuning job and its tuned model endpoint
    print(f"Fetching tuning job: {args.tuning_job_name}")
    tuning_job = client.tunings.get(name=args.tuning_job_name)
    if not tuning_job.tuned_model or not tuning_job.tuned_model.endpoint:
        raise ValueError("Tuning job does not have a deployed tuned model. Deploy the model to an endpoint.")
    tuned_endpoint = tuning_job.tuned_model.endpoint
    print(f"Using tuned model endpoint: {tuned_endpoint}")

    # Download and load the dataset
    df = download_dataset(args.source_bucket, args.source_path, args.local_path)
    df = df[df["label"].isin([0, 1])]
    df = df.sample(n=min(args.max_examples, len(df)), random_state=42)

    # Evaluate each example
    y_true = []
    y_pred = []
    start_time = time.time()
    for _, row in df.iterrows():
        prompt = prepare_prompt(row.get("subject", ""), row.get("body", ""))
        response = client.models.generate_content(
            model=tuned_endpoint,
            contents=prompt,
        )
        prediction = normalize_prediction(response.text)
        y_true.append(LABEL_MAPPING.get(row["label"], "benign"))
        y_pred.append(prediction)

    elapsed = time.time() - start_time
    results_df = pd.DataFrame({"label": y_true, "prediction": y_pred})
    metrics = compute_metrics(results_df)
    metrics["latency_total_sec"] = round(elapsed, 2)
    metrics["latency_avg_sec"] = round(
        elapsed / metrics["num_examples"], 3
    ) if metrics["num_examples"] else 0

    print("=== Fine-tuned Model Evaluation Summary ===")
    for k, v in metrics.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()