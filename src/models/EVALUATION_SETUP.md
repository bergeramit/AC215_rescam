# Setup Guide: Quantifying Fine-Tuning Improvements

## What You Need

### 1. **Gemini API Key** (Required)
The evaluation scripts use `google.generativeai` which requires a Gemini API key.

**Get your API key:**
1. Go to: https://makersuite.google.com/app/apikey
2. Create a new API key (or use existing one)
3. **Store it securely:**
   
   **Option A: Use `.env` file (Recommended - keeps key out of Git)**
   ```bash
   cd src/models
   # Create .env file (already in .gitignore)
   echo 'GEMINI_API_KEY="your-api-key-here"' > .env
   # Then load it:
   source .env
   ```
   
   **Option B: Export directly in terminal**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

**Why you need this:**
- `evaluate_classifier.py` uses `genai.GenerativeModel()` which needs the API key
- ADC (Application Default Credentials) might not have the right scopes for Generative AI API
- The API key is the most reliable way to authenticate

### 2. **Fine-Tuned Model ID** (Required)
You need the model resource name from Vertex AI after fine-tuning completes.

**Get it from:**
- Vertex AI Console → Tuning Jobs → Your job → "Tuned Model" field
- Or run: `python3 check_finetuned_model.py` (it will print the model resource name)

**Format:** `projects/1097076476714/locations/us-east1/models/1234567890@1`

### 3. **GCS Access** (Already have this)
- Your ADC credentials already work for GCS
- The script downloads `cleaned_dataset.parquet` from `gs://rescam-dataset-bucket/processed-dataset/`

### 4. **Python Dependencies** (Already installed)
- `google-generativeai`
- `google-cloud-storage`
- `pandas`
- `pyarrow`

## Step-by-Step Evaluation

### Step 1: Get Fine-Tuned Model ID
```bash
cd src/models
python3 check_finetuned_model.py
```
This will print the model resource name (e.g., `projects/.../models/123@1`)

### Step 2: Set API Key

**Option A: Using `.env` file (Recommended)**
```bash
cd src/models
source .env  # Loads GEMINI_API_KEY from .env file
```

**Option B: Export directly**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

### Step 3: Evaluate Baseline Model
```bash
python3 evaluate_classifier.py \
  --model-id gemini-2.0-flash-001 \
  --max-examples 200 \
  --output baseline_metrics.json
```

### Step 4: Evaluate Fine-Tuned Model
```bash
python3 evaluate_classifier.py \
  --model-id "projects/1097076476714/locations/us-east1/models/YOUR_MODEL_ID@1" \
  --max-examples 200 \
  --output finetuned_metrics.json
```

### Step 5: Compare Results
```bash
python3 compare_models.py \
  --baseline baseline_metrics.json \
  --finetuned finetuned_metrics.json
```

## What Metrics You'll Get

- **Accuracy**: Overall correctness
- **Precision (scam)**: Of emails predicted as scam, how many were actually scam
- **Recall (scam)**: Of actual scam emails, how many were correctly identified
- **False Positive Rate**: Benign emails incorrectly flagged as scam
- **False Negative Rate**: Scam emails missed (most critical!)
- **Latency**: Average response time per email

## Troubleshooting

**"403 Request had insufficient authentication scopes"**
- Solution: Set `GEMINI_API_KEY` environment variable (don't rely on ADC)

**"Model not found"**
- Solution: Make sure you're using the full model resource name from Vertex AI Console

**"Dataset not found"**
- Solution: Check that `gs://rescam-dataset-bucket/processed-dataset/cleaned_dataset.parquet` exists

## Quick Checklist

- [ ] Got Gemini API key from https://makersuite.google.com/app/apikey
- [ ] Exported `GEMINI_API_KEY` environment variable
- [ ] Got fine-tuned model ID from Vertex AI Console or `check_finetuned_model.py`
- [ ] Ran baseline evaluation → `baseline_metrics.json`
- [ ] Ran fine-tuned evaluation → `finetuned_metrics.json`
- [ ] Compared results → saw improvement metrics

