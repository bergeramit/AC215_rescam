import { useState, useEffect, useRef } from 'react'

function Inbox({ userEmail, onEventSourceReady }) {
  const [emails, setEmails] = useState([])
  const [connected, setConnected] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const [readEmails, setReadEmails] = useState(new Set())
  const [expandedEmails, setExpandedEmails] = useState(new Set())
  const eventSourceRef = useRef(null)

  useEffect(() => {
    if (!userEmail) return

    // Create SSE connection
    const eventSource = new EventSource(`/api/emails/stream?user=${encodeURIComponent(userEmail)}`)
    eventSourceRef.current = eventSource

    // Pass the event source up to parent so Classifications can use it too
    if (onEventSourceReady) {
      onEventSourceReady(eventSource)
    }

    eventSource.onopen = () => {
      console.log('SSE connection opened')
      setConnected(true)
    }

    // Listen for messages (SSE default event)
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'connected') {
          console.log('SSE connected event received')
          setConnected(true)
        } else if (data.type === 'new_email' && data.email) {
          const email = data.email
          // Add new email to the beginning of the list (newest first)
          setEmails(prevEmails => {
            // Check if email already exists to avoid duplicates
            if (prevEmails.some(e => e.id === email.id)) {
              return prevEmails
            }
            return [email, ...prevEmails]
          })
          // New emails are unread by default
        }
      } catch (error) {
        console.error('Error parsing SSE message:', error)
      }
    }

    eventSource.onerror = (error) => {
      const state = eventSource.readyState
      if (state === EventSource.CONNECTING) {
        setConnected(false)
      } else if (state === EventSource.CLOSED) {
        setConnected(false)
      }
    }

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [userEmail, onEventSourceReady])

  const truncateBody = (body, maxLength = 200) => {
    if (!body) return ''
    if (body.length <= maxLength) return body
    return body.substring(0, maxLength) + '...'
  }

  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const formatTime = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const toggleEmailExpanded = (emailId) => {
    setExpandedEmails(prev => {
      const newSet = new Set(prev)
      if (newSet.has(emailId)) {
        newSet.delete(emailId)
      } else {
        newSet.add(emailId)
        // Mark as read when expanded
        setReadEmails(prevRead => new Set([...prevRead, emailId]))
      }
      return newSet
    })
  }

  const isEmailUnread = (emailId) => {
    return !readEmails.has(emailId)
  }

  const isEmailExpanded = (emailId) => {
    return expandedEmails.has(emailId)
  }

  return (
    <div className="card" style={{
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      transition: 'all var(--transition-base)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 'var(--spacing-md) var(--spacing-lg)',
        borderBottom: isExpanded ? '1px solid var(--color-border)' : 'none',
        background: 'var(--color-surface)',
        cursor: 'pointer',
        userSelect: 'none'
      }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-md)',
          flex: 1
        }}>
          <div className={`collapse-icon ${!isExpanded ? 'collapsed' : ''}`}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3 style={{
            margin: 0,
            fontSize: 'var(--font-size-lg)',
            fontWeight: 'var(--font-weight-semibold)',
            color: 'var(--color-text-primary)'
          }}>
            Real-time Inbox
          </h3>
          {emails.length > 0 && (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: '24px',
              height: '24px',
              padding: '0 var(--spacing-xs)',
              background: 'var(--color-primary)',
              color: 'white',
              borderRadius: 'var(--radius-full)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 'var(--font-weight-semibold)'
            }}>
              {emails.length}
            </div>
          )}
        </div>
        <div className="status-indicator">
          <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></span>
          <span style={{
            fontSize: 'var(--font-size-sm)',
            color: connected ? 'var(--color-success)' : 'var(--color-error)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Content */}
      <div
        className={`collapsible-content ${isExpanded ? 'expanded' : 'collapsed'}`}
        style={{
          maxHeight: isExpanded ? '600px' : '0',
          transition: 'max-height var(--transition-slow), opacity var(--transition-base)',
          opacity: isExpanded ? 1 : 0
        }}
      >
        <div style={{
          padding: 0,
          maxHeight: '600px',
          overflowY: 'auto',
          background: 'var(--color-surface)'
        }}>
          {emails.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 'var(--spacing-2xl)',
              color: 'var(--color-text-secondary)',
              textAlign: 'center'
            }}>
              <div style={{
                fontSize: 'var(--font-size-sm)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: 'var(--font-weight-medium)'
              }}>
                No new emails yet
              </div>
              <div style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-text-tertiary)'
              }}>
                Waiting for incoming emails...
              </div>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--spacing-xs)'
            }}>
              {emails.map((email) => {
                const unread = isEmailUnread(email.id)
                const expanded = isEmailExpanded(email.id)

                return (
                  <div
                    key={email.id}
                    className={`${unread ? 'email-unread' : 'email-read'}`}
                    style={{
                      padding: 0,
                      border: 'none',
                      borderRadius: 0,
                      transition: 'all var(--transition-base)',
                      cursor: 'pointer'
                    }}
                    onClick={() => toggleEmailExpanded(email.id)}
                  >
                    {/* Collapsed Email Row */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-md)',
                      padding: 'var(--spacing-md)',
                      paddingLeft: 'var(--spacing-lg)',
                      borderBottom: '1px solid var(--color-border-light)',
                      transition: 'background-color var(--transition-base)'
                    }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                    >
                      {/* Unread Indicator */}
                      <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: 'var(--radius-full)',
                        background: unread ? 'var(--color-primary)' : 'transparent',
                        flexShrink: 0
                      }}></div>

                      {/* Sender */}
                      <div style={{
                        minWidth: '180px',
                        maxWidth: '180px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: unread ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
                        color: 'var(--color-text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flexShrink: 0
                      }}>
                        {email.sender || 'Unknown Sender'}
                      </div>

                      {/* Subject Only */}
                      <div style={{
                        flex: 1,
                        minWidth: 0
                      }}>
                        <div className="email-subject" style={{
                          fontSize: 'var(--font-size-base)',
                          fontWeight: unread ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
                          color: 'var(--color-text-primary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {email.subject || 'No Subject'}
                        </div>
                      </div>

                      {/* Timestamp */}
                      <div style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-text-tertiary)',
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                        minWidth: '80px',
                        textAlign: 'right'
                      }}>
                        {email.timestamp ? formatTime(email.timestamp) : ''}
                      </div>

                      {/* Expand/Collapse Icon */}
                      <div className={`collapse-icon ${!expanded ? 'collapsed' : ''}`} style={{ flexShrink: 0 }}>
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                    </div>

                    {/* Expanded Email Content */}
                    {expanded && (
                      <div
                        className="collapsible-content expanded"
                        style={{
                          padding: 'var(--spacing-lg)',
                          paddingLeft: 'var(--spacing-2xl)',
                          borderBottom: '1px solid var(--color-border-light)',
                          background: 'var(--color-surface)'
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 'var(--spacing-md)'
                        }}>
                          {/* Email Header */}
                          <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 'var(--spacing-xs)',
                            paddingBottom: 'var(--spacing-md)',
                            borderBottom: '1px solid var(--color-border)'
                          }}>
                            <div style={{
                              fontSize: 'var(--font-size-base)',
                              fontWeight: 'var(--font-weight-semibold)',
                              color: 'var(--color-text-primary)'
                            }}>
                              {email.subject || 'No Subject'}
                            </div>
                            <div style={{
                              fontSize: 'var(--font-size-sm)',
                              color: 'var(--color-text-secondary)'
                            }}>
                              <strong>From:</strong> {email.sender || 'Unknown Sender'}
                            </div>
                            {email.timestamp && (
                              <div style={{
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--color-text-tertiary)'
                              }}>
                                {formatDate(email.timestamp)} • {formatTime(email.timestamp)}
                              </div>
                            )}
                          </div>

                          {/* Email Body */}
                          <div style={{
                            color: 'var(--color-text-primary)',
                            fontSize: 'var(--font-size-base)',
                            lineHeight: 'var(--line-height-relaxed)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                          }}>
                            {email.body || email.snippet || 'No content'}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Inbox

