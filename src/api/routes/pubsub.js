import { PubSub } from '@google-cloud/pubsub'
import { notifyEmailUpdate } from './emails.js'
import { getGmailClient, getMessagesSinceHistoryId, getMessage } from '../services/gmailService.js'
import { classifyEmail } from '../services/modelService.js'
import { saveEmailClassification } from '../services/gcsService.js'
import { getStoredToken, getLastHistoryId, storeLastHistoryId } from '../services/tokenStore.js'
import { storeEmailInFirestore } from '../services/firestoreService.js'

const pubsub = new PubSub({
  projectId: process.env.GCP_PROJECT_ID
})

export async function handlePubSubWebhook(req, res) {
  try {
    // Pub/Sub push delivery sends messages in a specific format
    const message = req.body.message

    if (!message || !message.data) {
      return res.status(400).json({ error: 'Invalid message format' })
    }

    // Decode base64 message data
    const messageData = JSON.parse(
      Buffer.from(message.data, 'base64').toString('utf-8')
    )

    console.log(`[DEBUG] Pub/Sub webhook received. Keys: ${Object.keys(messageData).join(', ')}`)
    // Log all key-value pairs of messageData
    /*
    [DEBUG] messageData - name: "user-classifications/amitberger02@gmail.com/emails.json"
rescam-api       | [DEBUG] messageData - bucket: "rescam-user-emails"
rescam-api       | [DEBUG] messageData - generation: "1763919774805265"
rescam-api       | [DEBUG] messageData - metageneration: "1"
rescam-api       | [DEBUG] messageData - contentType: "application/json"
rescam-api       | [DEBUG] messageData - timeCreated: "2025-11-23T17:42:54.819Z"
rescam-api       | [DEBUG] messageData - updated: "2025-11-23T17:42:54.819Z"
rescam-api       | [DEBUG] messageData - storageClass: "STANDARD"
rescam-api       | [DEBUG] messageData - timeStorageClassUpdated: "2025-11-23T17:42:54.819Z"
rescam-api       | [DEBUG] messageData - size: "13937"
rescam-api       | [DEBUG] messageData - md5Hash: "8HNqXGP9czgS+7FxaIIr3A=="
rescam-api       | [DEBUG] messageData - mediaLink: "https://storage.googleapis.com/download/storage/v1/b/rescam-user-emails/o/user-classifications%2Famitberger02@gmail.com%2Femails.json?generation=1763919774805265&alt=media"
rescam-api       | [DEBUG] messageData - crc32c: "VJHVaQ=="
rescam-api       | [DEBUG] messageData - etag: "CJHa25zpiJEDEAE="
    */
    for (const [key, value] of Object.entries(messageData)) {
      console.log(`[DEBUG] messageData - ${key}: ${JSON.stringify(value)}`)
    }

    // Check if it's a GCS Notification
    if (messageData.kind === 'storage#object' && messageData.name && messageData.bucket) {
      console.log(`[DEBUG] Detected GCS Notification for file: ${messageData.name}`)
      res.status(200).send() // Acknowledge immediately

      // Process in background
      processGCSNotification(messageData).catch(err => {
        console.error(`[ERROR] Background GCS processing error:`, err)
      })
      return
    }

    // Otherwise assume Gmail Notification
    const userEmail = messageData.emailAddress
    const historyId = messageData.historyId

    // Disregard messages with undefined user ID
    if (!userEmail) {
      // Acknowledge receipt to prevent Pub/Sub from retrying
      return res.status(200).send()
    }

    console.log(`[DEBUG] Pub/Sub webhook received for ${userEmail}, historyId: ${historyId}`)

    // Acknowledge receipt immediately
    res.status(200).send()

    // Get stored access token
    const tokenData = await getStoredToken(userEmail)
    const accessToken = tokenData?.access_token || null

    if (!accessToken) {
      console.error(`[ERROR] No access token available for user: ${userEmail}`)
      console.error(`[ERROR] Message data keys:`, Object.keys(messageData))
      return
    }

    console.log(`[DEBUG] Access token found, processing notification for ${userEmail}`)

    // Process in background
    processGmailNotification(userEmail, historyId, accessToken).catch(err => {
      console.error(`[ERROR] Background processing error for ${userEmail}:`, err)
      console.error(`[ERROR] Stack trace:`, err.stack)
    })

  } catch (error) {
    console.error('Error handling Pub/Sub webhook:', error)
    res.status(500).send()
  }
}

async function processGmailNotification(userEmail, notificationHistoryId, accessToken) {
  try {
    console.log(`[DEBUG] ========== Processing Gmail Notification ==========`)
    console.log(`[DEBUG] User: ${userEmail}`)
    console.log(`[DEBUG] Notification historyId: ${notificationHistoryId}`)

    const gmail = await getGmailClient(accessToken)
    console.log(`[DEBUG] Gmail client created`)

    // Get the stored last processed historyId (baseline from watch setup)
    let lastProcessedHistoryId = await getLastHistoryId(userEmail)

    if (!lastProcessedHistoryId) {
      console.log(`[WARN] No stored historyId for ${userEmail}`)
      console.log(`[WARN] This should only happen if watch was set up before this code was deployed`)
      console.log(`[WARN] Please re-setup Gmail monitoring to store the initial historyId`)
      // Fallback: use notificationHistoryId directly (might miss some messages, but better than erroring)
      lastProcessedHistoryId = notificationHistoryId
    } else {
      console.log(`[DEBUG] Using stored lastProcessedHistoryId: ${lastProcessedHistoryId}`)
    }

    // Query from the stored historyId, not the notification historyId
    // This ensures we get all messages since the last processed point
    console.log(`[DEBUG] Querying from stored historyId: ${lastProcessedHistoryId}`)
    const messageIds = await getMessagesSinceHistoryId(gmail, lastProcessedHistoryId)
    console.log(`[DEBUG] Found ${messageIds.length} new message(s)`)

    if (messageIds.length === 0) {
      console.log(`[WARN] No new messages found for ${userEmail}`)
      console.log(`[DEBUG] Notification historyId: ${notificationHistoryId}, Last processed: ${lastProcessedHistoryId}`)
      // Still update the historyId even if no messages found (notification was sent for a reason)
      await storeLastHistoryId(userEmail, notificationHistoryId)
      return
    }

    console.log(`[INFO] Processing ${messageIds.length} message(s) for ${userEmail}`)

    // Process each message
    for (const messageId of messageIds) {
      try {
        console.log(`[ERROR] Processing message ${messageId}`)

        // Fetch full message
        const message = await getMessage(gmail, messageId)
        console.log(`[ERROR] Message ${messageId} fetched successfully`)

        // Store raw email in Firestore
        await storeEmailInFirestore(userEmail, message, messageId)

        // Parse email content
        const emailContent = parseGmailMessage(message)
        const metadata = extractGmailMetadata(message)
        console.log(`[ERROR] Email parsed - Subject: ${metadata.subject}, From: ${metadata.sender}`)

        // Extract body text for early notification
        const bodyText = extractBodyText(message)

        // Send early notification via SSE (before classification)
        const earlyEmailData = {
          id: messageId,
          threadId: message.threadId || '',
          receivedAt: new Date(parseInt(message.internalDate)).toISOString(),
          sender: metadata.sender,
          subject: metadata.subject,
          snippet: message.snippet || '',
          body: bodyText,
          timestamp: new Date().toISOString()
        }
        notifyEmailUpdate(userEmail, earlyEmailData, 'new_email')
        console.log(`[SUCCESS] Processed email ${messageId} for ${userEmail}`)
      } catch (error) {
        console.error(`[ERROR] Error processing message ${messageId}:`, error.message)
        console.error(`[ERROR] Stack trace:`, error.stack)
      }
    }

    // Update the stored historyId to the notification historyId after successful processing
    // This ensures the next query starts from the correct point
    await storeLastHistoryId(userEmail, notificationHistoryId)
    console.log(`[DEBUG] Updated lastHistoryId to ${notificationHistoryId} for ${userEmail}`)

  } catch (error) {
    console.error(`[ERROR] Error processing Gmail notification for ${userEmail}:`, error.message)
    console.error(`[ERROR] Stack trace:`, error.stack)
  }
}

async function processGCSNotification(fileData) {
  try {
    const fileName = fileData.name

    // Check if it's the emails.json file we care about
    // Path format: user-classifications/{userEmail}/emails.json
    const match = fileName.match(/^user-classifications\/(.+)\/emails\.json$/)

    if (!match) {
      console.log(`[DEBUG] Ignoring GCS update for unrelated file: ${fileName}`)
      return
    }

    const userEmail = match[1]
    console.log(`[INFO] Detected email classification update for ${userEmail}`)

    // We don't need to download the file here necessarily, 
    // we can just notify the client to fetch it, or fetch and send.
    // Let's fetch and send to be consistent with the previous plan.

    // Import dynamically to avoid circular dependency issues if any
    const { getEmailClassifications } = await import('../services/gcsService.js')

    const data = await getEmailClassifications(userEmail)

    // Notify client via SSE
    notifyEmailUpdate(userEmail, { emails: data.emails }, 'classification_update')
    console.log(`[SUCCESS] Sent classification update to ${userEmail}`)

  } catch (error) {
    console.error(`[ERROR] Error processing GCS notification:`, error)
  }
}

function parseGmailMessage(message) {
  const payload = message.payload || {}
  const headers = payload.headers || []

  const subject = headers.find(h => h.name === 'Subject')?.value || 'No Subject'
  const sender = headers.find(h => h.name === 'From')?.value || 'Unknown'
  const date = headers.find(h => h.name === 'Date')?.value || ''

  let body = ''
  if (payload.parts) {
    for (const part of payload.parts) {
      if (part.mimeType === 'text/plain' && part.body?.data) {
        body = Buffer.from(part.body.data, 'base64').toString('utf-8')
        break
      }
    }
  } else if (payload.body?.data) {
    body = Buffer.from(payload.body.data, 'base64').toString('utf-8')
  }

  return `From: ${sender}\nSubject: ${subject}\nDate: ${date}\n\n${body}`
}

function extractGmailMetadata(message) {
  const headers = message.payload?.headers || []
  return {
    sender: headers.find(h => h.name === 'From')?.value || 'Unknown',
    subject: headers.find(h => h.name === 'Subject')?.value || 'No Subject',
    date: headers.find(h => h.name === 'Date')?.value || ''
  }
}

function extractBodyText(message) {
  const payload = message.payload || {}
  let body = ''

  if (payload.parts) {
    for (const part of payload.parts) {
      if (part.mimeType === 'text/plain' && part.body?.data) {
        body = Buffer.from(part.body.data, 'base64').toString('utf-8')
        break
      }
    }
  } else if (payload.body?.data) {
    body = Buffer.from(payload.body.data, 'base64').toString('utf-8')
  }

  return body
}
