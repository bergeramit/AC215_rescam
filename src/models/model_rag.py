"""
Running with this command:
python3 model_rag.py --project_id 1097076476714 --index_endpoint_id 3044332193032699904 --deployed_index_id phishing_emails_deployed_1760372787396
"""
import argparse
import logging
import os
import pandas as pd
from google.cloud import aiplatform, storage
from vertexai.language_models import TextEmbeddingModel
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

INSTRUCTION_PROMPT = """
You are an intelligent email risk classifier.
You receive the **current email** (body and optional headers) and a **retrieval-augmented context (RAG)** containing samples of this user’s previous emails.

---

## Objective

Classify the email as one of:

* **benign** — expected or legitimate message
* **spam** — unsolicited or irrelevant marketing/bulk message
* **scam** — deceptive or malicious message attempting to obtain money, credentials, or sensitive information
* **suspicious** — signals of risk present, but insufficient evidence for clear classification

Provide a **short, evidence-based rationale** explaining why you chose that label.

---

## What the RAG contains

The RAG includes past messages, both legitimate and malicious, with metadata such as:

* sender name and address
* domain
* subject lines
* message snippets or short summaries
* timestamp
* (optional) known labels like *spam*, *scam*, or *benign*

You can conceptually use this information to:

* Identify whether this sender or domain has appeared before
* Check if similar wording, tone, or formatting matches known spam/scam patterns
* See if similar messages were legitimate in the past
* Detect unusual senders, domains, or topics compared to the user’s historical communication

---

## Classification Heuristics

Consider:

* Sender identity and domain similarity to known contacts
* Lookalike domains or spoofing attempts
* Unusual reply-to addresses
* Urgent or threatening language
* Requests for payments, credentials, or MFA codes
* Suspicious attachments or links (e.g., shortened, IP-only, mismatched anchors)
* Thread hijacking or fake invoice/inquiry patterns
* DKIM/SPF/DMARC information if available
* Consistency with previous legitimate correspondence from the RAG

---

## Output Format

Return **only** a single JSON object in the following structure:

```json
{{
  "classification": "benign | spam | scam | suspicious",
  "confidence": 0.0,
  "primary_reason": "≤40 words summarizing the decisive signals",
  "indicators": [
    "mismatched_sender",
    "lookalike_domain",
    "unknown_sender_no_history",
    "urgent_language",
    "payment_request",
    "credential_harvest",
    "attachment_risky",
    "link_shortener",
    "dkim_spf_dmarc_fail",
    "thread_hijack",
    "known_contact_match",
    "bulk_marketing_traits",
    "headers_missing",
    "rag_empty"
  ],
  "evidence": [
    {{
      "source": "current_email",
      "quote": "short quote…"
    }},
    {{
      "source": "rag",
      "quote": "short quote or match summary…"
    }}
  ],
  "parsed": {{
    "sender_display": "…",
    "sender_email": "…",
    "from_domain": "…",
    "reply_to": "…",
    "links": ["list of extracted domains/URLs if any"],
    "attachments": ["names/extensions if any"],
    "headers_used": true
  }},
  "recommended_action": "allow | quarantine | warn_user | block_sender | report_phishing"
}}
```

---

## Inputs

```
CURRENT_EMAIL_BODY:
---
{email_content}
---

RAG_CONTEXT:
---
{rag_context}
---
```

**Now:**
Use the email and relevant RAG context to infer risk, then output your classification and reasoning strictly in the JSON format above — no extra text or commentary.
"""


def fetch_rag_context(
    query_text: str,
    project_id: str,
    location: str,
    index_endpoint_id: str,
    deployed_index_id: str,
    num_neighbors: int = 5,
) -> str:
    """Fetches relevant context from Vertex AI Vector Search.

    Args:
        query_text: The email content to search for.
        project_id: Google Cloud project ID.
        location: GCP region for Vertex AI resources.
        index_endpoint_id: The ID of the Vertex AI Index Endpoint.
        deployed_index_id: The ID of the deployed index on the endpoint.
        num_neighbors: Number of similar emails to retrieve.

    Returns:
        A string containing the formatted RAG context.
    """
    logging.info("Fetching RAG context from Vertex AI Vector Search...")
    aiplatform.init(project=project_id, location=location)

    # Use Vertex AI Text Embedding API instead of sentence-transformers
    # This eliminates the need for PyTorch and local model downloads
    model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    embeddings = model.get_embeddings([query_text])
    # embeddings[0].values returns a list of floats, which is what we need
    query_embedding = list(embeddings[0].values)

    # Query the index
    index_endpoint_name = f"projects/{project_id}/locations/{location}/indexEndpoints/{index_endpoint_id}"
    endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name)

    response = endpoint.find_neighbors(
        deployed_index_id=deployed_index_id,
        queries=[query_embedding],  # Already a list, no need for .tolist()
        num_neighbors=num_neighbors,
    )

    # Format results
    context_str = "No similar emails found.\n"
    if not response or not response[0]:
        return context_str

    try:
        metadata_df = pd.read_parquet("email_metadata.parquet")
        has_metadata = True
    except FileNotFoundError:
        logging.warning("Metadata file 'email_metadata.parquet' not found.")
        has_metadata = False

    lines = []
    for neighbor in response[0]:
        line = f"- ID: {neighbor.id}, Distance: {neighbor.distance:.4f}"
        if has_metadata:
            email_data = metadata_df[metadata_df['email_id'] == neighbor.id]
            if not email_data.empty:
                row = email_data.iloc[0]
                line += f", Sender: {row['sender']}, Subject: {row['subject']}, Label: {'PHISHING' if row['label'] == 1 else 'LEGITIMATE'}"
        lines.append(line)

    return "\n".join(lines)


def read_email_from_gcs(bucket_name: str, file_name: str) -> str:
    """Reads the content of an email from a GCS bucket."""
    logging.info(f"Reading email '{file_name}' from bucket '{bucket_name}'.")
    try:
        storage_client = storage.Client(project=bucket_name)
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        email_content = blob.download_as_text()
        return email_content
    except Exception as e:
        logging.error(f"Failed to read from GCS: {e}")
        raise


def classify_email_with_rag(
    project_id: str,
    location: str,
    index_endpoint_id: str,
    deployed_index_id: str,
    gcs_bucket_name: str,
    gcs_file_name: str,
) -> str:
    """Classifies an email using a RAG-enabled generative model.

    Args:
        project_id: Your Google Cloud project ID.
        location: The GCP region for your resources.
        index_endpoint_id: The ID of the Vertex AI Index Endpoint.
        deployed_index_id: The ID of the deployed index.
        gcs_bucket_name: The GCS bucket containing the email.
        gcs_file_name: The email file to classify.

    Returns:
        The classification result as a JSON string.
    """
    # 1. Initialize Vertex AI for RAG (keep us-east1 for Vector Search)
    logging.info(f"Initializing Vertex AI for project '{project_id}' in '{location}'.")
    # Note: We don't use vertexai for the generative model, only for Vector Search
    # vertexai.init(project=project_id, location=location)

    # 2. Read email content from GCS
    email_content = read_email_from_gcs(gcs_bucket_name, gcs_file_name)

    # 3. Fetch RAG context from Vector Search
    
    
    #TODO: Harry => we need a new RAG without sentence-transformers
    
    # rag_context = fetch_rag_context(
    #     query_text=email_content,
    #     project_id=project_id,
    #     location=location,
    #     index_endpoint_id=index_endpoint_id,
    #     deployed_index_id=deployed_index_id,
    # )
    rag_context = ""

    # 4. Configure Gemini API with API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it with your Google Gemini API key."
        )
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-09-2025")

    # 5. Construct the prompt and generate content
    prompt = INSTRUCTION_PROMPT.format(
        email_content=email_content, rag_context=rag_context
    )

    logging.info("Sending request to the Gemini API...")
    response = model.generate_content(prompt)

    classification = response.text.strip()
    logging.info(f"Classification result: {classification}")

    return classification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify an email using a vector-search-based RAG model."
    )
    parser.add_argument("--project_id", default="1097076476714", help="Your Google Cloud project ID.")
    parser.add_argument(
        "--location",
        default="us-east1",
        help="The GCP region for your resources (e.g., 'us-east1').",
    )
    parser.add_argument(
        "--index_endpoint_id",
        default="3044332193032699904",
        help="The ID of your Vertex AI Index Endpoint."
    )
    parser.add_argument(
        "--deployed_index_id",
        default="phishing_emails_deployed_1760372787396",
        help="The ID of the deployed index on the endpoint.",
    )
    parser.add_argument(
        "--gcs_bucket_name",
        default="rescam-dataset-bucket",
        help="GCS bucket with the email file.",
    )
    parser.add_argument(
        "--gcs_file_name",
        default="example_last_email.txt",
        help="Name of the email file in the GCS bucket.",
    )
    args = parser.parse_args()

    result = classify_email_with_rag(
        project_id=args.project_id,
        location=args.location,
        index_endpoint_id=args.index_endpoint_id,
        deployed_index_id=args.deployed_index_id,
        gcs_bucket_name=args.gcs_bucket_name,
        gcs_file_name=args.gcs_file_name,
    )

    print(f"\nThe email '{args.gcs_file_name}' is classified as: \n{result}")