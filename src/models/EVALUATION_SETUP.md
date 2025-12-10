# Evaluation Setup

## What You Need

### 1. Gemini API Key
Get it from https://makersuite.google.com/app/apikey

Put it in `.env` file:
```bash
cd src/models
echo 'GEMINI_API_KEY="your-key-here"' > .env
source .env
```

Or export it:
```bash
export GEMINI_API_KEY="your-key-here"
```

### 2. Fine-Tuned Model ID
Get it from Vertex AI Console or run `check_finetuned_model.py`

Format: `projects/1097076476714/locations/us-east1/models/1234567890@1`

### 3. GCS Access
Already set up - scripts download from `gs://rescam-dataset-bucket/processed-dataset/`

## Running Evaluation

1. Get model ID:
```bash
cd src/models
python3 check_finetuned_model.py
```

2. Set API key:
```bash
source .env
```

3. Run baseline:
```bash
python3 evaluate_classifier.py --model-id gemini-2.0-flash-001 --max-examples 200 --output baseline_metrics.json
```

4. Run fine-tuned:
```bash
python3 evaluate_finetuned_via_genai.py --tuning-job-name projects/.../tuningJobs/... --max-examples 200
```

5. Compare:
```bash
python3 compare_models.py --baseline baseline_metrics.json --finetuned finetuned_metrics.json
```

## Metrics

- Accuracy, precision, recall, F1 (for both scam and benign)
- False positive/negative rates
- Latency

## Common Issues

**403 error**: Set GEMINI_API_KEY env var

**Model not found**: Use full resource name from Vertex AI Console

**Dataset not found**: Check GCS bucket path

