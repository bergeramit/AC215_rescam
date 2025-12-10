#!/usr/bin/env python3
"""
Access fine-tuned Gemini model via Vertex AI endpoint.

Fine-tuned models in Vertex AI must be deployed to an endpoint before use.
This script shows how to access the model after deployment.
"""
import vertexai
from google.cloud import aiplatform

PROJECT_ID = "1097076476714"
REGION = "us-east1"
MODEL_NAME = "projects/1097076476714/locations/us-east1/models/1064762662291767296@1"

def deploy_model_to_endpoint():
    """Deploy the fine-tuned model to an endpoint."""
    vertexai.init(project=PROJECT_ID, location=REGION)
    
    # Get the model
    model = aiplatform.Model(MODEL_NAME)
    
    # Deploy to endpoint
    endpoint = model.deploy(
        deployed_model_display_name="phishing-classifier-endpoint",
        machine_type="n1-standard-4",  # Adjust as needed
        min_replica_count=1,
        max_replica_count=1,
    )
    
    print(f"✅ Model deployed to endpoint: {endpoint.resource_name}")
    return endpoint


def use_model_via_endpoint(endpoint_name: str, prompt: str):
    """Use the deployed model via endpoint."""
    vertexai.init(project=PROJECT_ID, location=REGION)
    
    endpoint = aiplatform.Endpoint(endpoint_name)
    
    # Format input for Gemini fine-tuned model
    instances = [{
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]
    }]
    
    response = endpoint.predict(instances=instances)
    return response


if __name__ == "__main__":
    print("=" * 70)
    print("Fine-Tuned Model Access via Endpoint")
    print("=" * 70)
    print()
    print("Fine-tuned Gemini models in Vertex AI must be deployed to an endpoint.")
    print("This is a one-time setup step.")
    print()
    print("To deploy:")
    print("1. Run: endpoint = deploy_model_to_endpoint()")
    print("2. Save the endpoint name")
    print("3. Use: use_model_via_endpoint(endpoint_name, prompt)")
    print()
    print("Or deploy via Console:")
    print("https://console.cloud.google.com/vertex-ai/models")
    print("  → Select your model")
    print("  → Click 'Deploy to endpoint'")


