import { useState, useEffect, useRef } from 'react'
import ClassificationItem from './ClassificationItem'
import { getStoredToken } from '../auth/googleAuth'

function Classifications({ userEmail, eventSource }) {
    const [emails, setEmails] = useState([])
    const [isExpanded, setIsExpanded] = useState(true)
    const seenEmailIdsRef = useRef(new Set())
    const [loading, setLoading] = useState(true)

    // DEBUG: Print current state
    // console.log('Rendering Classifications, emails count:', emails.length)

    // Fetch initial email classifications on mount
    useEffect(() => {
        const fetchInitialEmails = async () => {
            console.log('[Classifications] fetchInitialEmails called, userEmail:', userEmail)

            if (!userEmail) {
                console.log('[Classifications] No userEmail, skipping fetch')
                setLoading(false)
                return
            }

            try {
                setLoading(true)
                const token = getStoredToken()
                console.log('[Classifications] Got token:', token ? 'exists' : 'null')

                if (!token) {
                    console.error('[Classifications] No token found in localStorage')
                    setLoading(false)
                    return
                }

                console.log('[Classifications] Fetching from /api/emails...')
                const response = await fetch('/api/emails', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                console.log('[Classifications] Response status:', response.status)

                if (!response.ok) {
                    const errorText = await response.text()
                    console.error('[Classifications] Error response:', errorText)
                    throw new Error(`HTTP error! status: ${response.status}`)
                }

                const data = await response.json()
                console.log('[Classifications] Received data:', data)

                if (data.emails && Array.isArray(data.emails)) {
                    // Set initial emails (newest first, as they come from GCS)
                    setEmails(data.emails)

                    // Populate seenEmailIds to prevent duplicates from SSE
                    data.emails.forEach(email => {
                        seenEmailIdsRef.current.add(email.id)
                    })

                    console.log(`[Classifications] Loaded ${data.emails.length} initial classifications`)
                } else {
                    console.log('[Classifications] No emails in response or invalid format')
                }
            } catch (error) {
                console.error('[Classifications] Error fetching initial emails:', error)
                // Don't block UI, just log the error
                // SSE updates will still work
            } finally {
                setLoading(false)
                console.log('[Classifications] Loading complete')
            }
        }

        fetchInitialEmails()
    }, [userEmail])

    // Listen to SSE messages for new classification updates
    useEffect(() => {
        if (!eventSource) return

        const handleMessage = (event) => {
            try {
                // DEBUG: Print raw event data
                // console.log('Received SSE message in Classifications:', event.data)
                const data = JSON.parse(event.data)
                // console.log('Parsed SSE data:', data)
                // console.log('Current seenEmailIds:', Array.from(seenEmailIdsRef.current))

                if (data.type === 'classification_update' && data.email && data.email.emails) {
                    const incomingEmails = data.email.emails
                    // console.log('Received classification update', incomingEmails.length)

                    // Filter out emails we've already seen (using ref.current)
                    const newEmails = incomingEmails.filter(email => !seenEmailIdsRef.current.has(email.id))

                    if (newEmails.length > 0) {
                        // Update the ref's Set directly (no state update needed)
                        newEmails.forEach(email => seenEmailIdsRef.current.add(email.id))

                        // Prepend new emails to the top of the list
                        setEmails(prev => [...newEmails, ...prev])

                        // console.log(`Added ${newEmails.length} new classification(s)`)
                    } else {
                        console.log('No new emails to add (all already seen)')
                    }
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
                    transition: 'max-height var(--transition-slow), opacity var(--transition-base)',
                    opacity: isExpanded ? 1 : 0
                }}
            >
                <div style={{
                    padding: 'var(--spacing-md)',
                    background: 'var(--color-surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--spacing-md)'
                }}>
                    {loading ? (
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
                                fontWeight: 'var(--font-weight-medium)'
                            }}>
                                Loading classifications...
                            </div>
                        </div>
                    ) : emails.length === 0 ? (
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
                            <ClassificationItem key={email.id} item={email} />
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}

export default Classifications
