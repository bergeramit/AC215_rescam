# Fine-Tuning Status Summary

## Context

We successfully fine-tuned a Gemini 2.0 Flash model for phishing email classification on Vertex AI.

**Project Details:**
- Project ID: `1097076476714`
- Region: `us-east1`
- Base Model: `gemini-2.0-flash-001`
- Fine-Tuned Model: `projects/1097076476714/locations/us-east1/models/1064762662291767296@1`
- Training Data: `gs://rescam-rag-bucket/fine-tuning/finetune_20251118_212544/training_data.jsonl`
- Training Script: `src/models/train_model.py`

**What We've Done:**
1. ✅ Created training data in JSONL format (Gemini 2.0 format with `contents` field)
2. ✅ Uploaded training data to GCS
3. ✅ Created fine-tuning job via Vertex AI SFT API (`vertexai.tuning.sft.train()`)
4. ✅ Fine-tuning job completed successfully
5. ✅ Model created in Vertex AI Model Registry

## Current Issue

**Problem:** We cannot directly access the fine-tuned model for evaluation.

**What We Tried:**
1. `google.generativeai.GenerativeModel(model_id)` - Fails with "unexpected model name format"
2. `vertexai.generative_models.GenerativeModel(model_id)` - Fails with "400 Request contains an invalid argument"

**Root Cause:**
Fine-tuned Gemini models in Vertex AI **must be deployed to an endpoint** before they can be used. Unlike base models (which can be accessed directly via `google.generativeai`), fine-tuned models require:
1. Deployment to a Vertex AI endpoint
2. Access via `endpoint.predict()` API

**Current Status:**
- ✅ Fine-tuning job: **COMPLETE**
- ✅ Model created: **YES**
- ✅ Base model evaluation: **WORKS** (can evaluate `gemini-2.0-flash-001`)
- ❌ Fine-tuned model evaluation: **BLOCKED** (requires endpoint deployment)

## Next Steps

**Option 1: Deploy Model to Endpoint (for full evaluation)**
```python
from google.cloud import aiplatform
vertexai.init(project="1097076476714", location="us-east1")
model = aiplatform.Model("projects/1097076476714/locations/us-east1/models/1064762662291767296@1")
endpoint = model.deploy(
    deployed_model_display_name="phishing-classifier-endpoint",
    machine_type="n1-standard-4",
    min_replica_count=1,
    max_replica_count=1,
)
```

**Option 2: Document Current State (for Milestone 4)**
- Show fine-tuning job completed successfully
- Show model was created
- Run base model evaluation to demonstrate framework
- Note that fine-tuned model evaluation requires endpoint deployment (production step)

## Key Files

- `src/models/train_model.py` - Training script
- `src/models/evaluate_classifier.py` - Evaluation script (works for base model)
- `src/models/access_finetuned_via_endpoint.py` - Example endpoint deployment code
- `src/models/check_finetuned_model.py` - Sanity check script (currently blocked)

## API Differences

**Base Models:**
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-001")
response = model.generate_content(prompt)
```

**Fine-Tuned Models (after endpoint deployment):**
```python
from google.cloud import aiplatform
endpoint = aiplatform.Endpoint("projects/.../endpoints/...")
instances = [{"contents": [{"role": "user", "parts": [{"text": prompt}]}]}]
response = endpoint.predict(instances=instances)
```

## Questions to Resolve

1. Do we need to deploy the endpoint now, or can we document the current state for Milestone 4?
2. If deploying, what machine type and scaling should we use?
3. How do we want to structure the evaluation comparison (base vs fine-tuned)?

