import { useState, useEffect, useRef } from 'react'
import { getStoredUser, signOut, getStoredToken } from '../auth/googleAuth'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import Inbox from './Inbox'
import Classifications from './Classifications'
import Sidebar from './Sidebar'

function Dashboard() {
  const user = getStoredUser()
  const navigate = useNavigate()
  const [isWatching, setIsWatching] = useState(false)
  const [loading, setLoading] = useState(false)
  const [eventSource, setEventSource] = useState(null)

  // Initialize theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('rescam-theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  // Automatically start monitoring when component mounts
  useEffect(() => {
    const autoStartMonitoring = async () => {
      // Only start if not already watching and user is authenticated
      if (!isWatching && !loading && user) {
        await startWatching()
      }
    }

    autoStartMonitoring()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  const startWatching = async () => {
    try {
      setLoading(true)
      const token = getStoredToken()

      if (!token) {
        alert('Please sign in first')
        navigate('/')
        return
      }

      await axios.post(
        '/api/gmail/watch',
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setIsWatching(true)
    } catch (error) {
      console.error('Error starting watch:', error)
      alert('Error starting Gmail watch: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSignOut = () => {
    signOut()
    navigate('/')
  }

  if (!user) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        color: 'var(--color-text-secondary)'
      }}>
        Not authenticated
      </div>
    )
  }

  // Get user initials for avatar
  const getInitials = (email) => {
    if (!email) return 'U'
    const parts = email.split('@')[0].split('.')
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return email[0].toUpperCase()
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--color-background)',
      display: 'flex'
    }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        marginLeft: 'var(--sidebar-width)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh'
      }}>
        {/* Header */}
        <header style={{
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          padding: 'var(--spacing-md) 0',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{
            padding: '0 var(--spacing-lg)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 'var(--spacing-lg)'
          }}>
            {/* Title */}
            <div style={{
              fontSize: 'var(--font-size-base)',
              color: 'var(--color-text-secondary)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Email Security Dashboard
            </div>

            {/* User Section */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-md)'
            }}>
              {/* User Info */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)',
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--color-surface-hover)'
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--color-primary)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  flexShrink: 0
                }}>
                  {getInitials(user.email)}
                </div>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px'
                }}>
                  <div style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: 'var(--color-text-primary)',
                    lineHeight: 1.2
                  }}>
                    {user.name || user.email.split('@')[0]}
                  </div>
                  <div style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-tertiary)',
                    lineHeight: 1.2
                  }}>
                    {user.email}
                  </div>
                </div>
              </div>

              {/* Sign Out Button - Subtle Secondary */}
              <button
                onClick={handleSignOut}
                className="btn btn-ghost"
                style={{
                  fontSize: 'var(--font-size-sm)',
                  padding: 'var(--spacing-sm) var(--spacing-md)',
                  color: 'var(--color-text-secondary)'
                }}
              >
                Sign Out
              </button>
            </div>
          </div>
        </header>

        {/* Toolbar Section */}
        <div style={{
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          padding: 'var(--spacing-md) 0'
        }}>
          <div style={{
            padding: '0 var(--spacing-lg)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 'var(--spacing-lg)'
          }}>
            <div style={{
              fontSize: 'var(--font-size-base)',
              color: 'var(--color-text-secondary)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Gmail Monitoring
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-sm)',
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: isWatching ? 'var(--color-surface-hover)' : 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-primary)'
            }}>
              {loading ? (
                <>
                  <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--color-text-tertiary)',
                    display: 'inline-block',
                    animation: 'pulse 1.5s ease-in-out infinite'
                  }}></span>
                  <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Starting Monitoring...</span>
                </>
              ) : isWatching ? (
                <>
                  <span className="status-dot connected"></span>
                  <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Monitoring Active</span>
                </>
              ) : (
                <>
                  <span className="status-dot disconnected"></span>
                  <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Monitoring Inactive</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main style={{
          flex: 1,
          padding: 'var(--spacing-xl) var(--spacing-lg)',
          overflowY: 'auto'
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: 'var(--spacing-xl)'
          }}>
            {/* Inbox Section */}
            <div>
              <Inbox userEmail={user.email} onEventSourceReady={setEventSource} />
            </div>

            {/* Classifications Section */}
            <div>
              <Classifications userEmail={user.email} eventSource={eventSource} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Dashboard
