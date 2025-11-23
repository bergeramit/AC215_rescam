# GCS Notification Setup Guide

To enable real-time updates when classifications are saved to Google Cloud Storage, you need to configure your GCS bucket to send notifications to the Pub/Sub topic that your application is already listening to.

## Prerequisites

- `gcloud` CLI installed and authenticated.
- The name of your GCS bucket (e.g., `rescam-dataset-bucket`).
- The name of your Pub/Sub topic (e.g., `gmail-notifications`).

## Setup Steps

### 1. Set Variables

```bash
# Replace with your actual values
BUCKET_NAME="rescam-user-emails"
TOPIC_NAME="gmail-notifications"
PROJECT_ID="articulate-fort-472520-p2"
```

### 2. Grant Permissions

Allow GCS to publish messages to your Pub/Sub topic.

```bash
# Get the GCS service account email
GCS_SA_EMAIL=$(gcloud storage service-agent --project=$PROJECT_ID)

# Grant the publisher role
gcloud pubsub topics add-iam-policy-binding $TOPIC_NAME \
    --member="serviceAccount:$GCS_SA_EMAIL" \
    --role="roles/pubsub.publisher" \
    --project=$PROJECT_ID
```

### 3. Create Notification Configuration

Tell the bucket to send a message to the topic whenever a file is finalized (created or overwritten).

```bash
gcloud storage buckets notifications create gs://$BUCKET_NAME \
    --topic=$TOPIC_NAME \
    --event-types=OBJECT_FINALIZE \
    --payload-format=JSON \
    --project=$PROJECT_ID
```

Output:

```bash
etag: '2'
event_types:
- OBJECT_FINALIZE
id: '2'
kind: storage#notification
payload_format: JSON_API_V1
selfLink: https://www.googleapis.com/storage/v1/b/rescam-user-emails/notificationConfigs/2
topic: //pubsub.googleapis.com/projects/articulate-fort-472520-p2/topics/gmail-notifications
```

### 4. Verify

Upload a test file to the bucket and check if a message arrives in your subscription.

```bash
# Create a dummy file
echo "test" > test.txt

# Upload
gcloud storage cp test.txt gs://$BUCKET_NAME/test.txt

# Check subscription (if you have a pull subscription for debugging)
# gcloud pubsub subscriptions pull ...
```

