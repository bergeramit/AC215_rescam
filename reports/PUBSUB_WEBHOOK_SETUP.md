# Pub/Sub Webhook Setup Guide

## The Problem

You successfully set up Gmail Watch, which means:
- ✅ Gmail is publishing notifications to your Pub/Sub topic: `gmail-notifications`
- ✅ Messages are arriving in Pub/Sub (you can see them with ack_ids)

However, your webhook endpoint (`/api/pubsub/webhook`) is **not being called** because:

**Pub/Sub needs a PUSH subscription configured with a public webhook URL to deliver messages to your endpoint.**

Currently, you have a subscription (`gmail-notifications-sub`) but it's configured as a **PULL** subscription (empty `pushConfig`), which means:
- Messages sit in the subscription waiting to be manually pulled
- Your webhook endpoint is never called automatically

## Solution: Create a Push Subscription

### Step 1: Expose Your Local API Publicly

Since your API runs on `localhost:5050`, Pub/Sub can't reach it. Use one of these tools:

#### Option A: ngrok (Easiest)
```bash
# Install ngrok (if not installed)
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start ngrok tunnel
ngrok http 5050

# Note the HTTPS URL it gives you, e.g.:
# Forwarding  https://abc123.ngrok.io -> http://localhost:5050
```

#### Option B: cloudflared (Cloudflare Tunnel)
```bash
# Install cloudflared (if not installed)
brew install cloudflared  # macOS

# Start tunnel
cloudflared tunnel --url http://localhost:5050

# Note the HTTPS URL it gives you
```

### Step 2: Create Push Subscription

#### Using the Setup Script (Recommended)
```bash
# Make sure ngrok/cloudflared is running and note the URL
# Then run:
./setup-pubsub-push.sh https://abc123.ngrok.io/api/pubsub/webhook
```

#### Manual Setup
```bash
PROJECT_ID="articulate-fort-472520-p2"
WEBHOOK_URL="https://your-ngrok-url.ngrok.io/api/pubsub/webhook"

# Delete old pull subscription if exists
gcloud pubsub subscriptions delete gmail-notifications-sub \
  --project=$PROJECT_ID

# Create new push subscription
gcloud pubsub subscriptions create gmail-notifications-push \
  --topic=gmail-notifications \
  --push-endpoint=$WEBHOOK_URL \
  --project=$PROJECT_ID
```

### Step 3: Verify

1. **Check subscription:**
   ```bash
   gcloud pubsub subscriptions describe gmail-notifications-push \
     --project=articulate-fort-472520-p2
   ```
   
   Should show:
   ```yaml
   pushConfig:
     pushEndpoint: https://your-url.ngrok.io/api/pubsub/webhook
   ```

2. **Test the webhook:**
   ```bash
   # Send a test email to your Gmail account
   # Watch API logs:
   docker logs -f rescam-api
   
   # You should see:
   # [ERROR] Pub/Sub webhook received for your-email@gmail.com, historyId: ...
   ```

3. **Monitor Pub/Sub messages:**
   ```bash
   # Check if messages are being delivered
   gcloud pubsub subscriptions pull gmail-notifications-push \
     --limit=5 \
     --project=articulate-fort-472520-p2 \
     --auto-ack
   ```

## Alternative: Use Pull Subscription (Different Approach)

If you can't expose your API publicly, you would need to switch to a pull model where your API actively polls Pub/Sub. However, this requires different code architecture and is not what your current webhook handler expects.

## Troubleshooting

### Webhook not receiving messages?

1. **Check subscription type:**
   ```bash
   gcloud pubsub subscriptions describe gmail-notifications-push \
     --project=articulate-fort-472520-p2 | grep pushConfig
   ```
   - Should show `pushEndpoint`, not empty

2. **Test webhook endpoint directly:**
   ```bash
   curl -X POST https://your-ngrok-url.ngrok.io/api/pubsub/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

3. **Check Pub/Sub message format:**
   - Gmail sends messages in a specific format
   - Your webhook expects: `req.body.message.data` (base64 encoded)

4. **Verify ngrok/cloudflared is running:**
   - The tunnel must stay active
   - If you restart, you'll get a new URL and need to update the subscription

### Error: "Invalid push endpoint"

- Ensure URL uses HTTPS (not HTTP)
- URL must be publicly accessible
- Endpoint must return 200 OK (even if processing fails)

## Production Deployment

For production, deploy your API to a publicly accessible service:
- Google Cloud Run
- App Engine
- Cloud Functions
- Any cloud service with public HTTPS endpoint

Then update the push subscription endpoint URL.

