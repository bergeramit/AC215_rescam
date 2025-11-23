import { useState, useEffect } from 'react'
import EmailItem from './EmailItem'

function Classifications({ userEmail, eventSource }) {
    const [emails, setEmails] = useState([])
    const [isExpanded, setIsExpanded] = useState(true)

    useEffect(() => {
        if (!eventSource) return

        const handleMessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'classification_update' && data.email && data.email.emails) {
                    console.log('Received classification update', data.email.emails.length)
                    setEmails(data.email.emails)
                }
            } catch (error) {
                console.error('Error parsing SSE message in Classifications:', error)
            }
        }

        eventSource.addEventListener('message', handleMessage)

        return () => {
            eventSource.removeEventListener('message', handleMessage)
        }
    }, [eventSource])

    return (
        <div className="card" style={{
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            transition: 'all var(--transition-base)',
            marginTop: 'var(--spacing-xl)'
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
                        Classifications
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
            </div>

            {/* Content */}
            <div
                className={`collapsible-content ${isExpanded ? 'expanded' : 'collapsed'}`}
                style={{
                    maxHeight: isExpanded ? '800px' : '0',
                    transition: 'max-height var(--transition-slow), opacity var(--transition-base)',
                    opacity: isExpanded ? 1 : 0
                }}
            >
                <div style={{
                    padding: 'var(--spacing-md)',
                    maxHeight: '800px',
                    overflowY: 'auto',
                    background: 'var(--color-surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--spacing-md)'
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
                                No classifications yet
                            </div>
                            <div style={{
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--color-text-tertiary)'
                            }}>
                                Waiting for analysis...
                            </div>
                        </div>
                    ) : (
                        emails.map((email) => (
                            <EmailItem key={email.id} email={email} />
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}

export default Classifications
