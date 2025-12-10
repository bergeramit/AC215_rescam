# Fine-Tuning Status

## What We Did

Fine-tuned Gemini 2.0 Flash for phishing classification.

- Project: 1097076476714
- Region: us-east1
- Base: gemini-2.0-flash-001
- Fine-tuned: projects/1097076476714/locations/us-east1/models/1064762662291767296@1
- Training data: gs://rescam-rag-bucket/fine-tuning/finetune_20251118_212544/training_data.jsonl

Steps:
1. Created JSONL training data (Gemini 2.0 format)
2. Uploaded to GCS
3. Created fine-tuning job via Vertex AI
4. Job completed successfully
5. Model in Vertex AI Model Registry

## Accessing Fine-Tuned Model

Fine-tuned models need to be deployed to an endpoint first. Can't use them directly like base models.

Base models work with `google.generativeai.GenerativeModel()`, but fine-tuned models need endpoint deployment and use `endpoint.predict()`.

The tuning job automatically created an endpoint, so we can use that for evaluation.

## Status

- Fine-tuning job: ✅ Complete
- Model created: ✅ Yes
- Endpoint: ✅ Available (projects/1097076476714/locations/us-east1/endpoints/2729113204465598464)
- Evaluation: ✅ Works via endpoint

