import { getEmailClassifications } from '../services/gcsService.js'

const sseClients = new Map()

export async function getEmails(req, res) {
  try {
    const userEmail = req.user?.email
    if (!userEmail) {
      return res.status(401).json({ error: 'User email not found' })
    }

    const data = await getEmailClassifications(userEmail)
    res.json(data)
  } catch (error) {
    console.error('Error fetching emails:', error)
    res.status(500).json({ error: error.message })
  }
}

export function streamEmails(req, res) {
  const userEmail = req.query.user

  if (!userEmail) {
    return res.status(400).json({ error: 'User email required' })
  }

  // Set up SSE
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')

  // Store client connection
  if (!sseClients.has(userEmail)) {
    sseClients.set(userEmail, [])
  }
  sseClients.get(userEmail).push(res)

  // Send initial connection message
  res.write(`data: ${JSON.stringify({ type: 'connected' })}\n\n`)

  // Clean up on client disconnect
  req.on('close', () => {
    const clients = sseClients.get(userEmail)
    if (clients) {
      const index = clients.indexOf(res)
      if (index > -1) {
        clients.splice(index, 1)
      }
      if (clients.length === 0) {
        sseClients.delete(userEmail)
      }
    }
  })

  res.on('error', () => {
    // Clean up on error
    const clients = sseClients.get(userEmail)
    if (clients) {
      const index = clients.indexOf(res)
      if (index > -1) {
        clients.splice(index, 1)
      }
    }
  })
}

export function notifyEmailUpdate(userEmail, emailData, type = 'new_email') {
  const clients = sseClients.get(userEmail)
  if (clients) {
    const message = `data: ${JSON.stringify({ type, email: emailData })}\n\n`
    clients.forEach(client => {
      try {
        client.write(message)
      } catch (error) {
        console.error('Error sending SSE message:', error)
      }
    })
  }
}

