import { Storage } from '@google-cloud/storage'

const storage = new Storage({
  projectId: process.env.GCP_PROJECT_ID
})

const bucket = storage.bucket('rescam-user-emails')

export function getEmailClassificationsPath(userEmail) {
  return `user-classifications/${userEmail}/emails.json`
}

export async function getEmailClassifications(userEmail) {
  const filePath = getEmailClassificationsPath(userEmail)
  const file = bucket.file(filePath)

  try {
    const [exists] = await file.exists()
    if (!exists) {
      return { emails: [] }
    }

    const [contents] = await file.download()
    return JSON.parse(contents.toString())
  } catch (error) {
    console.error('Error reading email classifications:', error)
    return { emails: [] }
  }
}

export async function saveEmailClassification(userEmail, emailData) {
  const filePath = getEmailClassificationsPath(userEmail)
  const file = bucket.file(filePath)

  // Get existing emails
  const existing = await getEmailClassifications(userEmail)
  const emails = existing.emails || []

  // Check if email already exists, update it; otherwise add new
  const existingIndex = emails.findIndex(e => e.id === emailData.id)
  if (existingIndex >= 0) {
    emails[existingIndex] = emailData
  } else {
    emails.unshift(emailData) // Add to beginning
  }

  // Limit to last 100 emails for MVP
  if (emails.length > 100) {
    emails.splice(100)
  }

  // Save back to GCS
  await file.save(JSON.stringify({ emails }, null, 2), {
    contentType: 'application/json'
  })

  // Update timestamp file for change detection (triggers GCS notification)
  const timestampFile = bucket.file(`email-classifications/${userEmail}/latest-timestamp.txt`)
  await timestampFile.save(Date.now().toString(), {
    contentType: 'text/plain'
  })

  return emailData
}

