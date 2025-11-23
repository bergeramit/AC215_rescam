import { useState } from 'react'

function EmailItem({ email }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const getClassificationColor = (classification) => {
    if (!classification) return 'var(--color-pending)'
    const result = classification.result?.toLowerCase()
    if (result === 'benign') return 'var(--color-benign)'
    if (result === 'spam') return 'var(--color-spam)'
    if (result === 'scam') return 'var(--color-scam)'
    if (result === 'suspicious') return 'var(--color-suspicious)'
    return 'var(--color-pending)'
  }

  const getClassificationLabel = (classification) => {
    if (!classification) return 'Pending'
    return classification.result || 'Unknown'
  }

  const getBadgeClass = (classification) => {
    if (!classification) return 'badge badge-pending'
    const result = classification.result?.toLowerCase()
    if (result === 'benign') return 'badge badge-benign'
    if (result === 'spam') return 'badge badge-spam'
    if (result === 'scam') return 'badge badge-scam'
    if (result === 'suspicious') return 'badge badge-suspicious'
    return 'badge badge-pending'
  }

  return (
    <div className="card card-hover" style={{
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 0,
      overflow: 'hidden',
      transition: 'all var(--transition-base)'
    }}>
      {/* Header - Always Visible */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'start',
        padding: 'var(--spacing-md)',
        gap: 'var(--spacing-md)',
        cursor: 'pointer',
        userSelect: 'none'
      }}
      onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-sm)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            <div className={`collapse-icon ${!isExpanded ? 'collapsed' : ''}`}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div style={{
              fontSize: 'var(--font-size-base)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-text-primary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {email.subject || 'No Subject'}
            </div>
          </div>
          <div style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-secondary)',
            marginTop: 'var(--spacing-xs)',
            marginLeft: '28px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            From: {email.sender || 'Unknown'}
          </div>
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-sm)',
          flexShrink: 0
        }}>
          <span 
            className={getBadgeClass(email.classification)}
            style={{
              backgroundColor: getClassificationColor(email.classification)
            }}
          >
            {getClassificationLabel(email.classification)}
          </span>
        </div>
      </div>

      {/* Expandable Content */}
      <div 
        className={`collapsible-content ${isExpanded ? 'expanded' : 'collapsed'}`}
        style={{
          maxHeight: isExpanded ? '1000px' : '0',
          transition: 'max-height var(--transition-slow), opacity var(--transition-base)',
          opacity: isExpanded ? 1 : 0,
          overflow: 'hidden'
        }}
      >
        <div style={{
          padding: '0 var(--spacing-md) var(--spacing-md) var(--spacing-md)',
          borderTop: '1px solid var(--color-border)',
          marginTop: 'var(--spacing-xs)',
          paddingTop: 'var(--spacing-md)'
        }}>
          {email.snippet && (
            <div style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              lineHeight: 'var(--line-height-relaxed)',
              marginBottom: 'var(--spacing-md)',
              padding: 'var(--spacing-sm)',
              background: 'var(--color-surface-hover)',
              borderRadius: 'var(--radius-sm)'
            }}>
              {email.snippet}
            </div>
          )}
          
          {email.classification && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--spacing-xs)',
              padding: 'var(--spacing-sm)',
              background: 'var(--color-surface-hover)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 'var(--spacing-sm)'
            }}>
              <div style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-primary)',
                fontWeight: 'var(--font-weight-medium)'
              }}>
                Classification Details
              </div>
              <div style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-secondary)'
              }}>
                <strong>Confidence:</strong> {(email.classification.confidence * 100).toFixed(1)}%
              </div>
              {email.classification.primary_reason && (
                <div style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-secondary)',
                  marginTop: 'var(--spacing-xs)'
                }}>
                  <strong>Reason:</strong> {email.classification.primary_reason}
                </div>
              )}
            </div>
          )}
          
          <div style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-tertiary)',
            paddingTop: 'var(--spacing-sm)',
            borderTop: '1px solid var(--color-border-light)'
          }}>
            Received: {new Date(email.receivedAt).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  )
}

export default EmailItem

