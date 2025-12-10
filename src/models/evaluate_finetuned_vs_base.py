#!/usr/bin/env python3
"""
Compare base Gemini vs fine-tuned Gemini on phishing classification.

Usage:
    python3 evaluate_finetuned_vs_base.py \
        --tuning-job-name projects/1097076476714/locations/us-east1/tuningJobs/5730230261199667200 \
        --max-examples 200
"""
# projects/1097076476714/locations/us-east1/tuningJobs/5730230261199667200

import argparse
import os
import time

import pandas as pd
import google.generativeai as genai
from google.cloud import storage
import vertexai
from vertexai.tuning import sft
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

PROJECT_ID = "1097076476714"
LOCATION = "us-east1"
DEFAULT_BUCKET = "rescam-dataset-bucket"
DEFAULT_PATH = "processed-dataset/cleaned_dataset.parquet"
LABEL_MAPPING = {0: "benign", 1: "scam"}


def setup_genai():
    """Configure Google Generative AI SDK using API key."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your .env file or export it: "
            "export GEMINI_API_KEY='your-key-here'"
        )
    genai.configure(api_key=api_key)
    print("✅ Configured Gemini API with API key")


def download_dataset(bucket: str, path: str, local_path: str) -> pd.DataFrame:
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
    parser = argparse.ArgumentParser(description="Compare base vs fine-tuned Gemini on phishing emails")
    parser.add_argument(
        "--tuning-job-name",
        required=False,
        help="Tuning job resource name (e.g., projects/.../tuningJobs/...)",
    )
    parser.add_argument("--source-bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--source-path", default=DEFAULT_PATH)
    parser.add_argument("--local-path", default="eval_dataset.parquet")
    parser.add_argument("--max-examples", type=int, default=200)
    args = parser.parse_args()

    setup_genai()

    print("=" * 70)

    # Get fine-tuned model info from tuning job
    fine_tuned_model_id = None
    if args.tuning_job_name:
        print(f"Tuning job: {args.tuning_job_name}")
        try:
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            tuning_job = sft.SupervisedTuningJob(args.tuning_job_name)

            # Get the model resource name from the tuning job
            if hasattr(tuning_job, "tuned_model_name") and tuning_job.tuned_model_name:
                fine_tuned_model_id = tuning_job.tuned_model_name
                print(f"✅ Fine-tuned model: {fine_tuned_model_id}")
        except Exception as e:
            print(f"⚠️  Could not retrieve tuning job info: {e}")
            print("   Continuing with base model evaluation only.")
    else:
        print("No tuning job name provided.")

    base_model_id = "gemini-2.0-flash-001"
    print(f"Base model:    {base_model_id}")

    print("=" * 70)

    df = download_dataset(args.source_bucket, args.source_path, args.local_path)
    df = df[df["label"].isin([0, 1])]
    df = df.sample(n=min(args.max_examples, len(df)), random_state=42)

    def run_model_via_api(model_name: str):
        """Run evaluation on a model via google.generativeai API.

        NOTE: This only works for public Gemini models like 'gemini-2.0-flash-001'.
        Vertex-tuned models with names starting with 'projects/' cannot be used
        with google.generativeai and will be skipped.
        """
        if model_name.startswith("projects/"):
            print(f"⚠️  '{model_name}' looks like a Vertex AI model resource.")
            print("    This cannot be called via google.generativeai.GenerativeModel.")
            print("    Skipping evaluation for this model.\n")
            return pd.DataFrame([]), 0.0

        model = genai.GenerativeModel(model_name)
        results = []
        start = time.time()
        for _, row in df.iterrows():
            prompt = prepare_prompt(row.get("subject", ""), row.get("body", ""))
            try:
                response = model.generate_content(prompt)
                pred = normalize_prediction(response.text.strip())
            except Exception as exc:
                print(f"⚠️  Error: {exc}")
                pred = "unknown"

            results.append(
                {
                    "label": LABEL_MAPPING.get(row["label"], "benign"),
                    "prediction": pred,
                }
            )

        elapsed = time.time() - start
        return pd.DataFrame(results), elapsed

    print("\n🔄 Evaluating base model...")
    base_results, base_time = run_model_via_api(base_model_id)

    if base_results.empty:
        print("❌ Base model evaluation returned no results. Exiting.")
        return

    # Evaluate fine-tuned model if available
    tuned_results, tuned_time = None, 0.0
    if fine_tuned_model_id:
        print("\n🔄 Evaluating fine-tuned model via Generative AI API...")
        tuned_results, tuned_time = run_model_via_api(fine_tuned_model_id)
    else:
        print("\n⚠️  No fine-tuned model ID found; skipping fine-tuned evaluation.")

    base_metrics = compute_metrics(base_results)

    print("\n=== Base model metrics ===")
    for k, v in base_metrics.items():
        print(f"- {k}: {v}")
    print(f"latency_total_sec: {round(base_time, 2)}")
    print(f"latency_avg_sec:   {round(base_time / base_metrics['num_examples'], 3)}")

    if tuned_results is not None and not tuned_results.empty:
        tuned_metrics = compute_metrics(tuned_results)
        print("\n=== Fine-tuned model metrics ===")
        for k, v in tuned_metrics.items():
            print(f"- {k}: {v}")
        print(f"latency_total_sec: {round(tuned_time, 2)}")
        print(f"latency_avg_sec:   {round(tuned_time / tuned_metrics['num_examples'], 3)}")
    else:
        print("\n=== Fine-tuned model metrics ===")
        print("⚠️  Not evaluated (no fine-tuned model ID available or no results)")


if __name__ == "__main__":
    main()