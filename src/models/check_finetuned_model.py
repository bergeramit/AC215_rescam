#!/usr/bin/env python3
"""
Check fine-tuned model status and test it.
"""
import os
import sys
import google.generativeai as genai
from vertexai.tuning import sft
import vertexai

# Configuration
PROJECT_ID = "1097076476714"
REGION = "us-east1"
JOB_ID = "projects/1097076476714/locations/us-east1/tuningJobs/5730230261199667200"

def check_job_status():
    print("=" * 70)
    print("1. Checking Job Status...")
    print("=" * 70)
    
    try:
        vertexai.init(project=PROJECT_ID, location=REGION)
        job = sft.SupervisedTuningJob(JOB_ID)
        job_dict = job.to_dict()
        job_state = job_dict.get("state", str(job.state))
        tuned_model = (
            job_dict.get("tunedModel", {}).get("model")
            or getattr(job, "tuned_model_name", None)
            or getattr(job, "tuned_model", None)
        )
        
        print(f"Job State: {job_state}")
        print(f"Tuned Model: {tuned_model}")
        
        if job_state == "JOB_STATE_SUCCEEDED":
            if tuned_model:
                print("✅ Job completed successfully!")
                return tuned_model
            else:
                print("⚠️  Job succeeded but tuned model name not available yet.")
                return None
        elif job_state == "JOB_STATE_FAILED":
            print("❌ Job failed! Check Console for details.")
            return None
        elif job_state in {"JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED"}:
            print("⏳ Job still running...")
            return None
        else:
            print(f"⚠️  Job state: {job_state}")
            return tuned_model
            
    except Exception as e:
        print(f"❌ Error checking job: {e}")
        return None


def check_model_accessibility(model_resource):
    """Check if model can be loaded."""
    print("\n" + "=" * 70)
    print("2. Checking Model Accessibility...")
    print("=" * 70)
    
    try:
        # Vertex AI fine-tuned models must use Vertex AI API, not google.generativeai
        print("Using Vertex AI API for fine-tuned model...")
        vertexai.init(project=PROJECT_ID, location=REGION)
        from vertexai.generative_models import GenerativeModel, Part
        model = GenerativeModel(model_resource)
        print(f"✅ Model loaded: {model_resource}")
        
        # Test with a simple prompt to verify it works
        try:
            test_response = model.generate_content(
                Part.from_text("Say hello")
            )
            print("✅ Model is accessible and responding")
        except Exception as test_e:
            print(f"⚠️  Model loaded but generate_content test failed: {test_e}")
            print("   This might be a format issue - will try in actual tests")
        
        return model
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print(f"   This is a Vertex AI fine-tuned model - must use Vertex AI API")
        return None


def test_classification(model):
    """Test classification with known examples."""
    print("\n" + "=" * 70)
    print("3. Testing Classification...")
    print("=" * 70)
    
    # Test scam email
    scam_email = """Subject: URGENT: Verify Your Account

Dear Customer,

Your account will be suspended in 24 hours unless you click here: http://suspicious-link.com/verify

Click now to verify your account!
"""
    
    # Test benign email
    benign_email = """Subject: Meeting Tomorrow

Hi team,

Let's meet at 2pm tomorrow to discuss the project timeline.

Thanks!
"""
    
    test_cases = [
        ("scam", scam_email),
        ("benign", benign_email),
    ]
    
    all_passed = True
    
    for expected, email_text in test_cases:
        prompt = f"Classify this email as 'scam' or 'benign':\n\n{email_text}"
        
        try:
            # Try different formats for Vertex AI
            from vertexai.generative_models import Part
            
            # Try with Part object
            try:
                response = model.generate_content(Part.from_text(prompt))
            except:
                # Fallback to string in list
                response = model.generate_content([prompt])
            
            # Extract text from response
            if hasattr(response, 'text'):
                result = response.text.strip().lower()
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    result = candidate.content.parts[0].text.strip().lower()
                else:
                    result = str(candidate).strip().lower()
            else:
                result = str(response).strip().lower()
            
            if expected in result:
                print(f"✅ {expected.upper()} test: PASSED (got: {result})")
            else:
                print(f"❌ {expected.upper()} test: FAILED (expected '{expected}', got: {result})")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {expected.upper()} test: ERROR - {e}")
            all_passed = False
    
    return all_passed


def main():
    """Run all sanity checks."""
    print("\n" + "=" * 70)
    print("Fine-Tuned Model Sanity Check")
    print("=" * 70)
    print()
    
    # Check job status
    model_resource = check_job_status()
    
    if not model_resource:
        print("\n❌ Cannot proceed - job not completed or model not available")
        print("   Check the Console: https://console.cloud.google.com/vertex-ai/generative/language/locations/us-east1/tuning/tuningJob/5730230261199667200?project=1097076476714")
        sys.exit(1)
    
    # Check model accessibility
    model = check_model_accessibility(model_resource)
    
    if not model:
        print("\n❌ Cannot proceed - model not accessible")
        sys.exit(1)
    
    # Test classification
    tests_passed = test_classification(model)
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    if tests_passed:
        print("✅ All sanity checks passed!")
        print(f"\nModel Resource: {model_resource}")
        print("\nNext steps:")
        print("1. Update model_rag.py line 270 with the model resource name above")
        print("2. Test integration: python3 model_rag.py --project_id 1097076476714 --location us-east1")
    else:
        print("⚠️  Some tests failed. Review the output above.")
        print("   Model may need more training or different prompt format.")
    
    print()


if __name__ == "__main__":
    main()

