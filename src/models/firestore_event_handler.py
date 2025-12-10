"""
FastAPI server to handle Eventarc Firestore events
"""
import os
import json
import logging
import base64
import re
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import firestore, storage
from protobuf_schema.firestore_message_pb2 import DocumentEventData
from model_rag import classify_email_with_rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Firestore client with the specific database ID
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'articulate-fort-472520-p2')
DATABASE_ID = 'user-emails'
COLLECTION_NAME = 'user-emails-incoming'
GCS_BUCKET_NAME = 'rescam-user-emails'

# Model RAG configuration
LOCATION = os.getenv('VERTEX_AI_LOCATION', 'us-east1')
INDEX_ENDPOINT_ID = os.getenv('INDEX_ENDPOINT_ID', '3044332193032699904')
DEPLOYED_INDEX_ID = os.getenv('DEPLOYED_INDEX_ID', 'phishing_emails_deployed_1760372787396')

# Initialize Firestore client
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# Initialize GCS client
storage_client = storage.Client(project=PROJECT_ID)


def parse_protobuf_document(protobuf_data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse a Firestore DocumentEventData protobuf message to extract document information.

    Args:
        protobuf_data: Raw protobuf bytes representing a Firestore DocumentEventData

    Returns:
        Dictionary with document_id, collection, full_path, fields, etc. or None if parsing fails
    """
    try:
        # Parse the protobuf as a DocumentEventData
        event_data = DocumentEventData()
        event_data.ParseFromString(protobuf_data)

        # Get the document from the 'value' field (the new/current document state)
        if not event_data.HasField('value'):
            logger.warning("DocumentEventData has no 'value' field")
            return None

        document = event_data.value

        # Extract document path
        # Format: projects/{project}/databases/{database}/documents/{collection}/{doc_id}
        doc_path = document.name
        if not doc_path or '/documents/' not in doc_path:
            logger.warning(f"Invalid document path in protobuf: {doc_path}")
            return None

        # Parse the document path
        parts = doc_path.split('/documents/')
        if len(parts) < 2:
            logger.warning(f"Could not parse document path: {doc_path}")
            return None

        collection_and_doc = parts[1]
        path_parts = collection_and_doc.split('/')
        if len(path_parts) < 2:
            logger.warning(f"Could not extract collection and doc_id from: {collection_and_doc}")
            return None

        collection = path_parts[0]
        doc_id = path_parts[1]

        # Convert protobuf fields to Python dict
        fields_dict = {}
        for field_name, value in document.fields.items():
            fields_dict[field_name] = _convert_protobuf_value(value)

        return {
            'document_id': doc_id,
            'collection': collection,
            'full_path': doc_path,
            'fields': fields_dict,
            'create_time': document.create_time.seconds if document.create_time else None,
            'update_time': document.update_time.seconds if document.update_time else None
        }
    except Exception as e:
        logger.error(f"Error parsing protobuf document: {e}", exc_info=True)
        return None


def _convert_protobuf_value(value) -> Any:
    """
    Convert a Firestore protobuf Value to a Python native type.

    Args:
        value: A Firestore Value protobuf object

    Returns:
        Python native value (dict, list, str, int, float, bool, None, bytes)
    """
    # Check which value type is set
    if value.HasField('null_value'):
        return None
    elif value.HasField('boolean_value'):
        return value.boolean_value
    elif value.HasField('integer_value'):
        return value.integer_value
    elif value.HasField('double_value'):
        return value.double_value
    elif value.HasField('timestamp_value'):
        # Return as ISO format string
        ts = value.timestamp_value
        dt = datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9)
        return dt.isoformat() + 'Z'
    elif value.HasField('string_value'):
        return value.string_value
    elif value.HasField('bytes_value'):
        return value.bytes_value
    elif value.HasField('reference_value'):
        return value.reference_value
    elif value.HasField('geo_point_value'):
        gp = value.geo_point_value
        return {'latitude': gp.latitude, 'longitude': gp.longitude}
    elif value.HasField('array_value'):
        return [_convert_protobuf_value(v) for v in value.array_value.values]
    elif value.HasField('map_value'):
        result = {}
        for key, val in value.map_value.fields.items():
            result[key] = _convert_protobuf_value(val)
        return result
    else:
        logger.warning(f"Unknown value type in protobuf: {value}")
        return None


def parse_firestore_event(event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse Eventarc Firestore event to extract document information.
    
    Eventarc sends CloudEvents in Pub/Sub binding format (CE_PUBSUB_BINDING).
    The event contains a 'message' field with base64-encoded CloudEvent data.
    This function handles JSON format events.
    """
    import base64
    
    try:
        # Handle Pub/Sub binding format (CE_PUBSUB_BINDING)
        if 'message' in event_data:
            message = event_data['message']
            if 'data' in message:
                # Decode base64 CloudEvent data
                decoded_data = base64.b64decode(message['data']).decode('utf-8')
                cloud_event = json.loads(decoded_data)
                
                # CloudEvent has a 'data' field containing the Firestore event
                # Firestore event structure:
                # {
                #   "value": {
                #     "name": "projects/.../databases/.../documents/collection/doc_id",
                #     "fields": {...},
                #     "createTime": "...",
                #     "updateTime": "..."
                #   }
                # }
                firestore_event = cloud_event.get('data', {})
                
                if isinstance(firestore_event, str):
                    # Sometimes data is JSON string
                    firestore_event = json.loads(firestore_event)
                
                if 'value' in firestore_event:
                    value = firestore_event['value']
                    # Extract document path from name
                    # Format: projects/{project}/databases/{database}/documents/{collection}/{doc_id}
                    doc_path = value.get('name', '')
                    if '/documents/' in doc_path:
                        parts = doc_path.split('/documents/')
                        if len(parts) > 1:
                            collection_and_doc = parts[1]
                            path_parts = collection_and_doc.split('/')
                            if len(path_parts) >= 2:
                                collection = path_parts[0]
                                doc_id = path_parts[1]
                                return {
                                    'document_id': doc_id,
                                    'collection': collection,
                                    'full_path': doc_path,
                                    'fields': value.get('fields', {}),
                                    'create_time': value.get('createTime'),
                                    'update_time': value.get('updateTime')
                                }
        
        # Handle direct CloudEvents format (if not using Pub/Sub binding)
        if 'data' in event_data and 'source' in event_data:
            firestore_event = event_data.get('data', {})
            if isinstance(firestore_event, str):
                firestore_event = json.loads(firestore_event)
            
            if 'value' in firestore_event:
                value = firestore_event['value']
                doc_path = value.get('name', '')
                if '/documents/' in doc_path:
                    parts = doc_path.split('/documents/')
                    if len(parts) > 1:
                        collection_and_doc = parts[1]
                        path_parts = collection_and_doc.split('/')
                        if len(path_parts) >= 2:
                            collection = path_parts[0]
                            doc_id = path_parts[1]
                            return {
                                'document_id': doc_id,
                                'collection': collection,
                                'full_path': doc_path,
                                'fields': value.get('fields', {}),
                                'create_time': value.get('createTime'),
                                'update_time': value.get('updateTime')
                            }
        
        logger.warning(f"Could not parse event structure. Keys: {list(event_data.keys())}")
        return None
    except Exception as e:
        logger.error(f"Error parsing Firestore event: {e}", exc_info=True)
        raise


def parse_email_from_gmail_message(raw_email: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Parse Gmail API message format into email content string.
    Similar to gmail_processor.parse_email_message but works with stored raw email.
    
    Returns:
        Tuple of (email_content_string, metadata_dict)
    """
    payload = raw_email.get('payload', {})
    headers = payload.get('headers', [])
    
    # Extract headers
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    
    # Extract body
    body = ''
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
            elif part.get('mimeType') == 'text/html' and not body:
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    else:
        # Single part message
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    # Format email content for model_rag.py
    email_content = f"""From: {sender}
Subject: {subject}
Date: {date}

{body}
"""
    metadata = {
        'sender': sender,
        'subject': subject,
        'date': date,
        'snippet': raw_email.get('snippet', '')[:200]
    }
    
    return email_content, metadata


def save_classification_to_gcs(user_id: str, message_id: str, email_metadata: Dict[str, Any], 
                                classification_result: str) -> str:
    """
    Save email classification result to GCS bucket 'rescam-user-emails'.
    
    Args:
        user_id: User email address
        message_id: Gmail message ID
        email_metadata: Metadata about the email (sender, subject, etc.)
        classification_result: JSON string from classify_email_with_rag
        
    Returns:
        GCS path where classification was saved
    """
    try:
        # Parse classification result (it might be wrapped in markdown code blocks)
        classification_json = classification_result
        if '```json' in classification_json:
            json_start = classification_json.find('```json') + 7
            json_end = classification_json.find('```', json_start)
            classification_json = classification_json[json_start:json_end].strip()
        elif '```' in classification_json:
            json_start = classification_json.find('```') + 3
            json_end = classification_json.find('```', json_start)
            classification_json = classification_json[json_start:json_end].strip()
        
        try:
            classification_data = json.loads(classification_json)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logger.warning(f"Failed to parse classification JSON, using raw result")
            classification_data = {
                'classification': 'unknown',
                'confidence': 0.5,
                'primary_reason': classification_result[:200] if classification_result else 'Classification failed',
                'raw_result': classification_result
            }
        
        # Prepare email data with classification
        email_data = {
            'id': message_id,
            'threadId': email_metadata.get('thread_id', ''),
            'receivedAt': email_metadata.get('received_at', datetime.utcnow().isoformat() + 'Z'),
            'sender': email_metadata.get('sender', 'Unknown'),
            'subject': email_metadata.get('subject', 'No Subject'),
            'snippet': email_metadata.get('snippet', ''),
            'classification': classification_data,
            'processedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Save to GCS bucket
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Path: user-classifications/{user_id}/emails.json
        emails_path = f'user-classifications/{user_id}/emails.json'
        blob = bucket.blob(emails_path)
        
        # Get existing emails
        try:
            existing_data = json.loads(blob.download_as_text())
            emails = existing_data.get('emails', [])
        except:
            emails = []
        
        # Update or add email
        existing_index = next((i for i, e in enumerate(emails) if e['id'] == message_id), None)
        if existing_index is not None:
            emails[existing_index] = email_data
        else:
            emails.insert(0, email_data)  # Add to beginning
        
        # Save back
        blob.upload_from_string(
            json.dumps({'emails': emails}, indent=2),
            content_type='application/json'
        )
        
        logger.info(f"Saved classification for email {message_id} for user {user_id} to {emails_path}")
        return emails_path
        
    except Exception as e:
        logger.error(f"Error saving classification to GCS: {e}", exc_info=True)
        raise


@app.post("/route/firestore-incoming-email")
async def handle_firestore_event(request: Request):
    """
    Handle Eventarc POST event for new Firestore documents.
    Eventarc can send events in either JSON or protobuf format depending on the transport.
    """
    try:
        # Get the content type to determine format
        content_type = request.headers.get("content-type", "").lower()

        # Read the raw request body as bytes
        raw_body = await request.body()

        logger.info(f"Received Firestore event - Content-Type: {content_type}, Body size: {len(raw_body)} bytes")

        # Parse the event based on content type
        event_info = None

        if "application/protobuf" in content_type or "application/octet-stream" in content_type:
            # Handle protobuf format
            logger.info("Parsing event as protobuf format")
            event_info = parse_protobuf_document(raw_body)
        else:
            # Handle JSON format (default)
            logger.info("Parsing event as JSON format")
            try:
                event_data = json.loads(raw_body.decode('utf-8'))
                event_info = parse_firestore_event(event_data)
            except json.JSONDecodeError:
                # Try protobuf as fallback
                logger.info("JSON parsing failed, trying protobuf format")
                event_info = parse_protobuf_document(raw_body)

        if not event_info:
            logger.error("Failed to parse Firestore event from request")
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to parse Firestore event"}
            )

        document_id = event_info['document_id']
        collection = event_info['collection']
        
        logger.info(f"Processing Firestore event - Collection: {collection}, Document ID: {document_id}")
        
        # Verify it's from the correct collection
        if collection != COLLECTION_NAME:
            logger.warning(f"Event from unexpected collection: {collection}")
            return JSONResponse(
                status_code=200,
                content={"message": f"Ignored event from collection: {collection}"}
            )
        
        # Fetch the document from Firestore
        doc_ref = db.collection(COLLECTION_NAME).document(document_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"Document {document_id} does not exist in Firestore")
            return JSONResponse(
                status_code=404,
                content={"error": f"Document {document_id} not found"}
            )
        
        # Get document data
        doc_data = doc.to_dict()
        user_id = doc_data.get('user-id', 'unknown')
        raw_email = doc_data.get('raw-email', {})
        stored_at = doc_data.get('stored-at', 'unknown')
        message_id = doc_data.get('message-id', document_id)
        
        # Log the email information
        logger.info("=" * 80)
        logger.info(f"Email received from Firestore:")
        logger.info(f"  Document ID: {document_id}")
        logger.info(f"  Message ID: {message_id}")
        logger.info(f"  User ID: {user_id}")
        logger.info(f"  Stored at: {stored_at}")
        
        if not isinstance(raw_email, dict):
            logger.error(f"Raw email is not a dictionary: {type(raw_email)}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid raw email format"}
            )
        
        # Parse email from raw Gmail message
        logger.info("Parsing email from raw Gmail message...")
        try:
            email_content, email_metadata = parse_email_from_gmail_message(raw_email)
            logger.info(f"Email parsed - Subject: {email_metadata['subject']}, From: {email_metadata['sender']}")
        except Exception as e:
            logger.error(f"Error parsing email: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to parse email: {str(e)}"}
            )
        
        # Add thread_id and received_at from raw_email if available
        email_metadata['thread_id'] = raw_email.get('threadId', '')
        if 'internalDate' in raw_email:
            email_metadata['received_at'] = datetime.fromtimestamp(
                int(raw_email['internalDate']) / 1000
            ).isoformat() + 'Z'
        else:
            email_metadata['received_at'] = datetime.utcnow().isoformat() + 'Z'
        
        # Save email to temporary GCS location for classification
        logger.info("Saving email to temporary GCS location for classification...")
        temp_bucket_name = 'rescam-dataset-bucket'  # Use existing bucket for temp storage
        temp_file_name = f'temp-emails/{message_id}.txt'
        temp_blob = None
        
        try:
            temp_bucket = storage_client.bucket(temp_bucket_name)
            temp_blob = temp_bucket.blob(temp_file_name)
            temp_blob.upload_from_string(email_content, content_type='text/plain')
            logger.info(f"Email saved to temporary location: gs://{temp_bucket_name}/{temp_file_name}")
        except Exception as e:
            logger.error(f"Error saving email to temp GCS: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to save email to temp GCS: {str(e)}"}
            )
        
        # Classify email using model_rag
        logger.info("Classifying email with RAG model...")
        classification_result = None
        try:
            classification_result = classify_email_with_rag(
                project_id=PROJECT_ID,
                location=LOCATION,
                index_endpoint_id=INDEX_ENDPOINT_ID,
                deployed_index_id=DEPLOYED_INDEX_ID,
                gcs_bucket_name=temp_bucket_name,
                gcs_file_name=temp_file_name
            )
            logger.info(f"Classification complete: {classification_result[:200]}...")
        except Exception as e:
            logger.error(f"Error classifying email: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to classify email: {str(e)}"}
            )
        finally:
            # Clean up temp file
            if temp_blob:
                try:
                    temp_blob.delete()
                    logger.info(f"Cleaned up temporary file: {temp_file_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
        
        # Save classification result to GCS bucket 'rescam-user-emails'
        if not classification_result:
            logger.error("Classification result is None, cannot save to GCS")
            return JSONResponse(
                status_code=500,
                content={"error": "Classification failed - no result to save"}
            )
        
        logger.info("Saving classification result to GCS...")
        try:
            gcs_path = save_classification_to_gcs(
                user_id=user_id,
                message_id=message_id,
                email_metadata=email_metadata,
                classification_result=classification_result
            )
            logger.info(f"Classification saved to: gs://{GCS_BUCKET_NAME}/{gcs_path}")
        except Exception as e:
            logger.error(f"Error saving classification to GCS: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to save classification: {str(e)}"}
            )
        
        logger.info("=" * 80)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Email processed and classified successfully",
                "document_id": document_id,
                "user_id": user_id,
                "message_id": message_id,
                "gcs_path": gcs_path
            }
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON format"}
        )
    except Exception as e:
        logger.error(f"Error processing Firestore event: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

