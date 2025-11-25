# Milestone 4: Model Fine-Tuning Summary

**Project:** Rescam - Phishing Email Detection  
**Milestone:** 4 - Development and Deployment  
**Date:** November 2024

---

## 1. Training Scripts and Configuration Files

### Training Script
- **File:** `src/models/train_model.py`
- **Purpose:** Fine-tune Gemini 1.5 Flash model on labeled phishing email dataset
- **Key Features:**
  - Downloads dataset from GCS
  - Validates data quality
  - Converts to Gemini JSONL format
  - Creates Vertex AI fine-tuning job
  - Logs experiment metadata

### Configuration File
- **File:** `src/models/training_config.json`
- **Contents:**
  - Dataset source (bucket, path, label mapping)
  - Training parameters (max examples, base model, validation split)
  - Vertex AI configuration (project ID, region, bucket)
  - Deployment settings (model registry, version control)

### Usage
```bash
# Dry-run (validate without creating job)
python3 train_model.py --dry-run --max-examples 100

# Full fine-tuning
python3 train_model.py --max-examples 1000
```

---

## 2. Dataset References (Versioned)

### Dataset Source
- **GCS Path:** `gs://rescam-dataset-bucket/processed-dataset/cleaned_dataset.parquet`
- **Format:** Parquet (efficient, type-safe)
- **Total Size:** 82,486 labeled emails
- **Label Distribution:**
  - Phishing (label=1): 42,891 emails (52%)
  - Legitimate (label=0): 39,595 emails (48%)

### Dataset Versioning
Dataset version information is automatically tracked in experiment logs:

```json
{
  "dataset_version": {
    "dataset_path": "gs://rescam-dataset-bucket/processed-dataset/cleaned_dataset.parquet",
    "dataset_size_bytes": <size>,
    "dataset_updated": "<timestamp>",
    "num_examples": 82486,
    "label_distribution": {
      "1": 42891,
      "0": 39595
    }
  }
}
```

**Version Tracking:**
- Dataset path (immutable reference)
- File size and last updated timestamp
- Number of examples and label distribution
- All tracked in experiment logs saved to GCS

### Training Data Versioning
- **Format:** JSONL (one example per line)
- **GCS Path:** `gs://rescam-rag-bucket/fine-tuning/[experiment_name]/training_data.jsonl`
- **Experiment Name:** `finetune_YYYYMMDD_HHMMSS` (timestamp-based versioning)
- **Each experiment** creates a unique folder with timestamped training data

---

## 3. Experiment Logs

### Log Location
- **Local:** `experiment_log_[experiment_name].json` (created during dry-run)
- **GCS:** `gs://rescam-rag-bucket/experiments/[experiment_name]/experiment_log.json` (uploaded during full run)

### Log Contents
Each experiment log includes:

```json
{
  "experiment_name": "finetune_20251118_212209",
  "timestamp": "2025-11-18T21:22:09.123456",
  "dataset_version": {
    "dataset_path": "gs://rescam-dataset-bucket/processed-dataset/cleaned_dataset.parquet",
    "dataset_size_bytes": <size>,
    "dataset_updated": "<timestamp>",
    "num_examples": 82486,
    "label_distribution": {"1": 42891, "0": 39595}
  },
  "training_parameters": {
    "max_examples": 1000,
    "base_model": "gemini-1.5-flash",
    "num_training_examples": 1000
  },
  "job_id": "<vertex-ai-job-id>",
  "status": "started" | "dry_run" | "completed" | "failed"
}
```

### Reproducibility
- **Dataset version:** Tracked via GCS path, size, and timestamp
- **Training parameters:** All hyperparameters logged
- **Model version:** Job ID and fine-tuned model ID tracked
- **Full traceability:** Can reproduce any experiment from log

---

## 4. Training Process

### Overview
The fine-tuning process follows a structured pipeline to ensure reproducibility and quality:

1. **Data Preparation**
   - Download labeled dataset from GCS (`cleaned_dataset.parquet`)
   - Validate data quality (check columns, label distribution, minimum examples)
   - Shuffle dataset to ensure balanced sampling

2. **Data Transformation**
   - Convert parquet to JSONL format required by Gemini
   - Format emails as: `Subject: {subject}\n\n{body}`
   - Map binary labels (0/1) to text labels ("benign"/"scam")
   - Sample up to `max_examples` (default: 1000) with balanced distribution

3. **Training Data Upload**
   - Save JSONL locally for validation
   - Upload to GCS: `gs://rescam-rag-bucket/fine-tuning/[experiment_name]/training_data.jsonl`
   - Create timestamped experiment folder for versioning

4. **Fine-Tuning Job Creation**
   - Initialize Vertex AI with project and region
   - Create fine-tuning job via Vertex AI API
   - Job runs asynchronously (1-4 hours)
   - Monitor via GCP Console

5. **Experiment Logging**
   - Log all metadata (dataset version, parameters, job ID)
   - Save locally and upload to GCS
   - Enable full reproducibility

### Training Parameters
- **Base Model:** `gemini-1.5-flash`
- **Training Examples:** 1,000 (configurable via `--max-examples`)
- **Label Mapping:** 
  - `0` → `"benign"` (legitimate emails)
  - `1` → `"scam"` (phishing emails)
- **Region:** `us-central1`
- **Dataset:** 82,486 total emails (42,891 phishing, 39,595 legitimate)

### Validation Process
- **Pre-Training:** Dry-run mode validates data without creating job
- **Data Quality Checks:**
  - Minimum 100 examples required
  - Balanced label distribution (target: ~50/50)
  - Valid JSONL format
  - Required columns present (subject, body, label)

---

## 5. Results Summary

### Pre-Training Validation Results
- ✅ **Dataset Quality:** 82,486 emails with balanced labels (52% phishing, 48% legitimate)
- ✅ **Data Format:** Valid JSONL format with proper input/output structure
- ✅ **Label Balance:** 51% scam / 49% benign in training sample (excellent balance)
- ✅ **Data Validation:** All required columns present (subject, body, label)
- ✅ **Reproducibility:** Full dataset versioning and experiment logging in place

### Training Results
The fine-tuning job prepares the model for improved phishing detection. Expected improvements include:
- Better accuracy on phishing vs legitimate email classification
- Reduced false positives and false negatives
- Specialization on our specific dataset patterns

*Note: Actual training results will be updated after the fine-tuning job completes and the model is evaluated.*

---

## 6. Deployment Implications

### Current Deployment (Before Fine-Tuning)
- **Model:** Base Gemini 1.5 Flash via API
- **Classification:** Prompt engineering + RAG context
- **Accuracy:** Relies on general knowledge
- **Cost:** Pay-per-request API calls

### After Fine-Tuning
- **Model:** Fine-tuned Gemini model in Vertex AI Model Registry
- **Classification:** Specialized model + RAG context
- **Accuracy:** Expected improvement (specialized for phishing detection)
- **Cost:** Model hosting + inference costs

### Required Deployment Changes

#### 1. Update Model Reference
**File:** `src/models/model_rag.py`

**Before:**
```python
model = genai.GenerativeModel('gemini-1.5-flash')
```

**After:**
```python
# Get fine-tuned model ID from Vertex AI Console after training completes
fine_tuned_model_id = "models/[fine-tuned-model-id]"
model = genai.GenerativeModel(fine_tuned_model_id)
```

#### 2. Model Registry
- Register fine-tuned model in Vertex AI Model Registry
- Version the model (e.g., `v1.0`, `v1.1`)
- Enable rollback capability if new model performs worse

#### 3. Version Tracking
**File:** `src/models/firestore_event_handler.py`
- Update model version tracking
- Log which model version is used for each classification

#### 4. Deployment Strategy
- **Option A (Recommended):** Direct replacement of base model
- **Option B (Future):** A/B testing with gradual traffic shift

### Impact on System Architecture
- **No changes to RAG:** Vector Search and retrieval remain unchanged
- **No changes to API:** Same endpoints, just using different model
- **Model storage:** Fine-tuned model stored in Vertex AI (not local)
- **Monitoring:** Track model performance metrics in production

---

### Summary of Deployment Impact

**Key Changes Required:**
1. Update model reference in `model_rag.py` to use fine-tuned model ID
2. Register model in Vertex AI Model Registry for version control
3. Update model version tracking in `firestore_event_handler.py`
4. Monitor performance metrics in production

**No Changes Required:**
- RAG/Vector Search system (remains unchanged)
- API endpoints (same interface)
- Frontend/UI (no changes needed)

**Benefits:**
- Improved accuracy for phishing detection
- Reduced false positives/negatives
- Specialized model for our use case
- Better performance on email classification tasks

**Trade-offs:**
- Slightly higher cost (model hosting vs pay-per-request)
- Requires model management and versioning
- Longer initial setup time

---

## 7. Files and Artifacts

### Training Artifacts
1. **Training Script:** `src/models/train_model.py`
2. **Config File:** `src/models/training_config.json`
3. **Training Data:** `gs://rescam-rag-bucket/fine-tuning/[experiment]/training_data.jsonl`
4. **Experiment Logs:** `gs://rescam-rag-bucket/experiments/[experiment]/experiment_log.json`

### Documentation
1. **This Summary:** `src/models/MILESTONE4_FINETUNING_SUMMARY.md`

---

## 8. Reproducibility

### To Reproduce This Experiment

1. **Dataset:** Download from `gs://rescam-dataset-bucket/processed-dataset/cleaned_dataset.parquet`
2. **Config:** Use `src/models/training_config.json`
3. **Script:** Run `python3 train_model.py --max-examples 1000`
4. **Parameters:** All logged in experiment log JSON

### Version Control
- **Dataset:** GCS path + timestamp (immutable reference)
- **Training Data:** Timestamped experiment folders
- **Model:** Vertex AI Model Registry with version tags
- **Code:** Git repository with commit hashes

---

## 9. Next Steps

### Immediate (After Fine-Tuning Completes)
- [ ] Get fine-tuned model ID from Vertex AI Console
- [ ] Evaluate model on test set
- [ ] Compare performance with base model
- [ ] Update `model_rag.py` with fine-tuned model ID

### Short-Term
- [ ] Deploy to staging environment
- [ ] Test with sample emails
- [ ] Monitor performance metrics
- [ ] Document actual performance improvements

### Long-Term
- [ ] Collect more labeled data for next iteration
- [ ] Plan next fine-tuning run if needed
- [ ] Implement A/B testing framework
- [ ] Set up automated model evaluation

---

## Summary

This fine-tuning implementation provides:
- ✅ **Complete training pipeline** with validation and logging
- ✅ **Versioned datasets** with full traceability
- ✅ **Comprehensive experiment logs** for reproducibility
- ✅ **Clear deployment strategy** with required code changes
- ✅ **Documentation** for all components

The fine-tuned model is expected to improve classification accuracy by specializing the base Gemini model on our specific phishing email dataset, while maintaining compatibility with our existing RAG-based architecture.

