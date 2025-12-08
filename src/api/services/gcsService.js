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


