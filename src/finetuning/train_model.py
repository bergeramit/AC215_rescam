"""
Fine-tuning script for Gemini model on phishing email classification.

Downloads labeled emails, converts to Gemini JSONL format, and uploads to GCS.
"""
import argparse
import logging
import os
import json
import pandas as pd
from datetime import datetime
from google.cloud import storage
import vertexai
from vertexai.tuning import sft

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
PROJECT_ID = "1097076476714"
REGION = "us-east1"
BUCKET_NAME = "rescam-rag-bucket"

# Map binary labels to text labels for Gemini
LABEL_MAPPING = {
    0: "benign",
    1: "scam",
}


def download_training_data(source_bucket: str, source_path: str, local_path: str) -> pd.DataFrame:
    """Download dataset from GCS and validate it."""
    logger.info(f"Downloading from gs://{source_bucket}/{source_path}")
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(source_bucket)
    blob = bucket.blob(source_path)
    
    if not blob.exists():
        raise FileNotFoundError(f"File not found: gs://{source_bucket}/{source_path}")
    
    blob.download_to_filename(local_path)
    df = pd.read_parquet(local_path)
    
    logger.info(f"Loaded {len(df)} emails")
    logger.info(f"Labels: {df['label'].value_counts().to_dict()}")
    
    # Check we have enough data
    if len(df) < 100:
        raise ValueError(f"Not enough data: {len(df)} examples (need at least 100)")
    
    # Check required columns exist
    required_cols = ['subject', 'body', 'label']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    return df


def get_dataset_version(source_bucket: str, source_path: str) -> dict:
    """Get dataset version info for experiment logging."""
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(source_bucket)
    blob = bucket.blob(source_path)
    
    if not blob.exists():
        return {}
    
    return {
        "dataset_path": f"gs://{source_bucket}/{source_path}",
        "dataset_size_bytes": blob.size,
        "dataset_updated": blob.updated.isoformat() if blob.updated else None,
    }


def create_training_examples(df: pd.DataFrame, max_examples: int = 1000) -> list:
    """Convert DataFrame to Gemini JSONL format."""
    logger.info(f"Converting {len(df)} emails to training format...")
    
    # Shuffle to get balanced sample
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    examples = []
    for idx, row in df.iterrows():
        if len(examples) >= max_examples:
            break
        
        # Format email as subject + body
        subject = str(row.get('subject', ''))
        body = str(row.get('body', ''))
        email_text = f"Subject: {subject}\n\n{body}".strip()
        
        # Skip empty emails
        if len(email_text) < 10:
            continue
        
        # Convert 0/1 to text labels
        label = LABEL_MAPPING.get(row['label'], "benign")
        
        # Format for Gemini 2.0 fine-tuning
        # Gemini 2.0 requires "contents" field with parts structure
        # Format: {"contents": [{"role": "user", "parts": [{"text": "..."}]}, {"role": "model", "parts": [{"text": "..."}]}]}
        input_prompt = f"Classify this email as 'scam' or 'benign':\n\n{email_text}"
        
        examples.append({
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": input_prompt}]
                },
                {
                    "role": "model",
                    "parts": [{"text": label}]
                }
            ]
        })
    
    logger.info(f"Created {len(examples)} training examples")
    # Extract labels from contents structure
    labels = [e['contents'][1]['parts'][0]['text'] for e in examples]
    label_dist = pd.Series(labels).value_counts().to_dict()
    logger.info(f"Label distribution: {label_dist}")
    
    if len(examples) < 100:
        raise ValueError(f"Not enough examples: {len(examples)} (need at least 100)")
    
    return examples


def save_jsonl(examples: list, output_path: str):
    """Save examples as JSONL file."""
    logger.info(f"Saving {len(examples)} examples to {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"Saved {file_size:.2f} MB")


def upload_to_gcs(local_path: str, gcs_path: str) -> str:
    """Upload training data to GCS."""
    logger.info(f"Uploading to gs://{BUCKET_NAME}/{gcs_path}")
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    
    gcs_full_path = f"gs://{BUCKET_NAME}/{gcs_path}"
    logger.info(f"Uploaded to {gcs_full_path}")
    return gcs_full_path


def log_experiment(experiment_name: str, dataset_version: dict, training_params: dict, job_id: str = None, upload_to_gcs: bool = True) -> str:
    """Log experiment metadata."""
    log = {
        "experiment_name": experiment_name,
        "timestamp": datetime.now().isoformat(),
        "dataset_version": dataset_version,
        "training_parameters": training_params,
        "job_id": job_id,
        "status": "started" if job_id else "dry_run",
    }
    
    local_path = f"experiment_log_{experiment_name}.json"
    with open(local_path, 'w') as f:
        json.dump(log, f, indent=2)
    
    if upload_to_gcs:
        gcs_path = f"experiments/{experiment_name}/experiment_log.json"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        logger.info(f"Experiment log: gs://{BUCKET_NAME}/{gcs_path}")
        return f"gs://{BUCKET_NAME}/{gcs_path}"
    else:
        logger.info(f"Experiment log saved locally: {local_path}")
        return local_path


def create_fine_tuning_job(
    training_data_gcs_path: str, 
    model_display_name: str = "phishing-classifier",
    validation_data_gcs_path: str = None,
    epochs: int = None,
    learning_rate: float = None,
) -> str:
    """
    Create Gemini fine-tuning job using Vertex AI Supervised Tuning API.
    
    Args:
        training_data_gcs_path: GCS path to training JSONL file (required)
        model_display_name: Display name for the fine-tuned model (required)
        validation_data_gcs_path: Optional GCS path to validation JSONL file
        epochs: Optional number of training epochs (default: auto)
        learning_rate: Optional learning rate (default: auto)
    
    Returns:
        Job resource name (e.g., projects/.../locations/.../tuningJobs/...)
        
    Note:
        - Endpoint ID is NOT required for fine-tuning (only needed for model deployment/serving)
        - After training completes, the model will be available in Vertex AI Model Registry
        - Model resource name format: projects/{PROJECT_ID}/locations/{REGION}/models/{MODEL_ID}
        - Use the model resource name to update model_rag.py after training completes
    """
    logger.info(f"Creating Gemini fine-tuning job...")
    logger.info(f"Training data: {training_data_gcs_path}")
    if validation_data_gcs_path:
        logger.info(f"Validation data: {validation_data_gcs_path}")
    
    vertexai.init(project=PROJECT_ID, location=REGION)
    
    # Build training parameters
    train_params = {
        "source_model": "gemini-2.0-flash-001",
        "train_dataset": training_data_gcs_path,
        "tuned_model_display_name": model_display_name,
    }
    
    # Add optional parameters if provided
    if validation_data_gcs_path:
        train_params["validation_dataset"] = validation_data_gcs_path
    if epochs is not None:
        train_params["epochs"] = epochs
    if learning_rate is not None:
        train_params["learning_rate"] = learning_rate
    
    job = sft.train(**train_params)
    
    job_resource = job.resource_name
    logger.info("=" * 70)
    logger.info("Created Gemini tuning job:")
    logger.info(job_resource)
    logger.info("")
    logger.info("Monitor your job at:")
    logger.info(f"https://console.cloud.google.com/vertex-ai/studio?project={PROJECT_ID}&region={REGION}")
    logger.info("")
    logger.info("After training completes:")
    logger.info("1. Get the model resource name from Vertex AI Console")
    logger.info("2. Update model_rag.py to use the fine-tuned model:")
    logger.info("   model = genai.GenerativeModel('projects/{PROJECT_ID}/locations/{REGION}/models/{MODEL_ID}')")
    logger.info("=" * 70)
    
    return job_resource


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune Gemini for phishing detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run to validate data
  python3 train_model.py --dry-run --max-examples 100
  
  # Full fine-tuning with 1000 examples
  python3 train_model.py --max-examples 1000
  
  # With validation dataset
  python3 train_model.py --max-examples 1000 --validation-split 0.2

After training completes:
  1. Check Vertex AI Console for the model resource name
  2. Update model_rag.py line 270 to use the fine-tuned model:
     model = genai.GenerativeModel('projects/1097076476714/locations/us-east1/models/YOUR_MODEL_ID')
        """
    )
    parser.add_argument("--source-bucket", default="rescam-dataset-bucket", help="GCS bucket with dataset")
    parser.add_argument("--source-path", default="processed-dataset/cleaned_dataset.parquet", help="Dataset path in GCS")
    parser.add_argument("--max-examples", type=int, default=1000, help="Max training examples")
    parser.add_argument("--validation-split", type=float, default=None, help="Fraction of data to use for validation (0.0-1.0)")
    parser.add_argument("--epochs", type=int, default=None, help="Number of training epochs (default: auto)")
    parser.add_argument("--learning-rate", type=float, default=None, help="Learning rate (default: auto)")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't create job")
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("Gemini Fine-Tuning Pipeline")
    logger.info("=" * 70)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No job will be created")
    
    try:
        # Create experiment name
        experiment_name = f"finetune_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Download data
        local_parquet = "training_data.parquet"
        df = download_training_data(args.source_bucket, args.source_path, local_parquet)
        
        # Get dataset version info
        dataset_version = get_dataset_version(args.source_bucket, args.source_path)
        dataset_version["num_examples"] = len(df)
        dataset_version["label_distribution"] = df['label'].value_counts().to_dict()
        
        # Create training examples
        examples = create_training_examples(df, max_examples=args.max_examples)
        
        # Split into train/validation if requested
        validation_examples = None
        validation_gcs_path = None
        if args.validation_split and not args.dry_run:
            split_idx = int(len(examples) * (1 - args.validation_split))
            validation_examples = examples[split_idx:]
            examples = examples[:split_idx]
            logger.info(f"Split: {len(examples)} training, {len(validation_examples)} validation")
            
            # Save validation JSONL
            local_validation_jsonl = "validation_data.jsonl"
            save_jsonl(validation_examples, local_validation_jsonl)
            
            # Upload validation data
            validation_gcs_path = f"fine-tuning/{experiment_name}/validation_data.jsonl"
            validation_gcs_path = upload_to_gcs(local_validation_jsonl, validation_gcs_path)
        
        # Save training JSONL
        local_jsonl = "training_data.jsonl"
        save_jsonl(examples, local_jsonl)
        
        # Log experiment (only upload to GCS if not dry-run)
        training_params = {
            "max_examples": args.max_examples,
            "base_model": "gemini-2.0-flash-001",
            "num_training_examples": len(examples),
            "num_validation_examples": len(validation_examples) if validation_examples else 0,
            "validation_split": args.validation_split,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
        }
        
        if args.dry_run:
            log_experiment(experiment_name, dataset_version, training_params, upload_to_gcs=False)
        else:
            log_experiment(experiment_name, dataset_version, training_params)
        
        if args.dry_run:
            logger.info("=" * 70)
            logger.info("✅ DRY RUN COMPLETE - Data validated successfully!")
            logger.info(f"Created files: {local_parquet}, {local_jsonl}")
            logger.info(f"Training examples: {len(examples)}")
            logger.info("=" * 70)
            logger.info("To run full fine-tuning, remove --dry-run flag:")
            logger.info("  python3 train_model.py --max-examples 1000")
            return
        
        # Upload to GCS
        gcs_path = f"fine-tuning/{experiment_name}/training_data.jsonl"
        training_data_gcs = upload_to_gcs(local_jsonl, gcs_path)
        
        # Create fine-tuning job
        logger.info("\n" + "=" * 70)
        logger.info("Creating fine-tuning job (takes 1-4 hours)...")
        logger.info("Press Ctrl+C to cancel, or wait 5 seconds...")
        import time
        time.sleep(5)
        
        job_id = create_fine_tuning_job(
            training_data_gcs, 
            f"phishing-classifier-{experiment_name}",
            validation_data_gcs_path=validation_gcs_path,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
        )
        
        # Update log with job ID
        log_experiment(experiment_name, dataset_version, training_params, job_id)
        
        logger.info("=" * 70)
        logger.info("Fine-tuning job started!")
        logger.info(f"Job ID: {job_id}")
        
    except KeyboardInterrupt:
        logger.info("Cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
