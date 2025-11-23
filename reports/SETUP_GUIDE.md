# Rescam MVP Setup Guide

## Overview

This MVP implements:
- React frontend with Google Sign-In (direct OAuth, no Auth0)
- Node.js backend API
- Gmail push notifications via Pub/Sub
- Real-time email classification display
- Classification results stored in GCS bucket

## Prerequisites

1. Google Cloud Platform account (project ID: 1097076476714)
2. Gmail API enabled
3. Pub/Sub API enabled
4. GCS bucket: `rescam-dataset-bucket`

## Setup Steps

### 1. Google OAuth 2.0 Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized JavaScript origins:
   - `http://localhost:3000` (development)
4. Add authorized redirect URIs (not needed for Google Sign-In, but add for safety):
   - `http://localhost:3000`
5. Note your Client ID (you'll need this for frontend)
6. In OAuth consent screen, add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/userinfo.email`

### 2. Google Cloud Setup

#### Enable APIs
```bash
export PROJECT_ID=1097076476714
gcloud services enable gmail.googleapis.com --project=$PROJECT_ID
gcloud services enable pubsub.googleapis.com --project=$PROJECT_ID
gcloud services enable storage-api.googleapis.com --project=$PROJECT_ID
```

#### Create Pub/Sub Topic and Push Subscription
```bash
# Create topic
gcloud pubsub topics create gmail-notifications --project=$PROJECT_ID

# Grant Gmail API service account permission to publish
gcloud pubsub topics add-iam-policy-binding gmail-notifications \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project=$PROJECT_ID

# Create PUSH subscription pointing to your webhook endpoint
# IMPORTANT: Replace <YOUR_PUBLIC_WEBHOOK_URL> with a publicly accessible URL
# For local development, use ngrok or cloudflared to expose localhost:5050
# Example: https://abc123.ngrok.io/api/pubsub/webhook
gcloud pubsub subscriptions create gmail-notifications-push \
  --topic=gmail-notifications \
  --push-endpoint=<YOUR_PUBLIC_WEBHOOK_URL> \
  --project=$PROJECT_ID

Example:
`
gcloud pubsub subscriptions create gmail-notifications-push \
     --topic=gmail-notifications \
     --push-endpoint=https://prewireless-malaceous-earlie.ngrok-free.dev \
     --project=articulate-fort-472520-p2
`
# Or use the setup script:
# 1. Start ngrok: ngrok http 5050
# 2. Run: ./setup-pubsub-push.sh https://your-ngrok-url.ngrok.io/api/pubsub/webhook
```

#### Configure GCS Bucket Notifications (for push to Pub/Sub)
```bash
# Create notification configuration
gsutil notification create \
  -t gmail-notifications \
  -f json \
  -p email-classifications \ 
  gs://rescam-dataset-bucket
```

Note: OAuth 2.0 credentials are created in step 1 above.

### 3. Configure Environment Variables

#### Frontend (`src/app/.env`)
```env
VITE_GOOGLE_CLIENT_ID=your-google-oauth-client-id
VITE_API_URL=http://localhost:5050
```

#### Backend (`src/api/.env`)
```env
GOOGLE_CLIENT_ID=your-google-oauth-client-id
PORT=5050
GCP_PROJECT_ID=1097076476714
GCS_BUCKET_NAME=rescam-dataset-bucket
PUBSUB_TOPIC_NAME=gmail-notifications
```

### 4. Build and Run

```bash
# Build all services
docker-compose build

# Start services
docker-compose up frontend api

# In separate terminals, run other services as needed:
docker-compose up datapipeline  # For data preprocessing
docker-compose up models       # For model classification
```

### 5. Access Application

- Frontend: http://localhost:3000
- API: http://localhost:5050

## MVP Limitations

1. **OAuth Token Storage**: Currently uses in-memory storage. Tokens will be lost on restart. For production, use a database.
2. **Model Classification**: The API container calls `model_rag.py` via subprocess. This requires Python dependencies to be installed in the API container, or the model should run as a separate HTTP service.
3. **Gmail Watch Expiration**: Gmail watch expires after 7 days. Backend should auto-renew.
4. **GCS Notifications**: Currently, GCS notifications to Pub/Sub are set up, but the backend processes Gmail notifications directly (simplified for MVP).

## Testing Flow

1. Open http://localhost:3000
2. Click "Sign in with Google" button
3. Authorize Gmail access when prompted
4. Click "Start Gmail Monitoring" to set up Gmail watch
5. Send yourself a test email to the Gmail account you logged in with
6. The email should appear in the dashboard with classification results

## Troubleshooting

- **Gmail watch fails**: Ensure Pub/Sub topic exists and Gmail API service account has publish permission
- **Classification not working**: Check that model_rag.py dependencies are installed in API container, or run model as separate service
- **SSE not working**: Check browser console for connection errors, verify backend is running
- **Google Sign-In errors**: Verify Client ID is correct and OAuth consent screen is configured properly
- **Token verification fails**: Ensure GOOGLE_CLIENT_ID matches the one used in frontend

