#!/usr/bin/env python3
"""
Example: access fine-tuned model via Vertex AI endpoint.
"""
import vertexai
from google.cloud import aiplatform

PROJECT_ID = "1097076476714"
REGION = "us-east1"
MODEL_NAME = "projects/1097076476714/locations/us-east1/models/1064762662291767296@1"

def deploy_model_to_endpoint():
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
    print("Fine-tuned models need endpoint deployment.")
    print("Deploy via Console or use deploy_model_to_endpoint()")
    print("Then use use_model_via_endpoint(endpoint_name, prompt)")


