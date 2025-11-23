import { useState } from 'react'
import axios from 'axios'
import EmailItem from './EmailItem'
import { getStoredToken, getStoredUser } from '../auth/googleAuth'

function EmailList() {
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)
  const user = getStoredUser()

  const fetchEmails = async () => {
    try {
      setLoading(true)
      const token = getStoredToken()
      if (!token) {
        console.error('No token available')
        return
      }

      const response = await axios.get('/api/emails', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setEmails(response.data.emails || [])
      setHasFetched(true)
    } catch (error) {
      console.error('Error fetching emails:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <h2 style={{
          margin: 0,
          fontSize: 'var(--font-size-xl)',
          fontWeight: 'var(--font-weight-semibold)',
          color: 'var(--color-text-primary)'
        }}>
          Email Classifications
        </h2>
        <button
          onClick={fetchEmails}
          disabled={loading}
          className="btn btn-primary"
          style={{
            fontSize: 'var(--font-size-sm)',
            padding: 'var(--spacing-sm) var(--spacing-md)'
          }}
        >
          {loading ? 'Loading...' : 'Refresh Emails'}
        </button>
      </div>
      {loading && !hasFetched ? (
        <div style={{
          padding: 'var(--spacing-xl)',
          textAlign: 'center',
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--font-size-base)'
        }}>
          Loading emails...
        </div>
      ) : emails.length === 0 ? (
        <div className="card" style={{
          padding: 'var(--spacing-xl)',
          textAlign: 'center',
          color: 'var(--color-text-secondary)'
        }}>
          <p style={{
            margin: 0,
            fontSize: 'var(--font-size-base)',
            lineHeight: 'var(--line-height-relaxed)'
          }}>
            No emails classified yet. {hasFetched ? 'Click "Refresh Emails" to load them.' : 'Click "Refresh Emails" to fetch your email classifications.'}
          </p>
        </div>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--spacing-md)'
        }}>
          {emails.map((email) => (
            <EmailItem key={email.id} email={email} />
          ))}
        </div>
      )}
    </div>
  )
}

export default EmailList

