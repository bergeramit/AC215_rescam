import { useState } from 'react'

function ClassificationItem({ item }) {
    // DEBUG: Print the item being rendered
    // console.log('[ERROR] Rendering ClassificationItem:', item)

    const getClassificationColor = (result) => {
        if (!result) return 'var(--color-text-secondary)'
        const lower = result.toLowerCase()
        if (lower === 'benign') return 'var(--color-success)'
        if (lower === 'spam') return 'var(--color-warning)'
        if (lower === 'scam' || lower === 'phishing') return 'var(--color-error)'
        if (lower === 'suspicious') return 'var(--color-warning)'
        return 'var(--color-text-secondary)'
    }

    const getBadgeStyle = (result) => {
        const color = getClassificationColor(result)
        return {
            background: `${color}20`, // 20% opacity
            color: color,
            border: `1px solid ${color}40`,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-semibold)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
        }
    }

    const formatConfidence = (conf) => {
        return Math.round(conf * 100) + '%'
    }

    return (
        <div className="card" style={{
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 0,
            background: 'var(--color-surface)'
        }}>
            {/* Header - Always Visible */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'start',
                padding: 'var(--spacing-md)',
                gap: 'var(--spacing-md)'
            }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-sm)',
                        marginBottom: 'var(--spacing-xs)'
                    }}>
                        <div style={{
                            fontSize: 'var(--font-size-base)',
                            fontWeight: 'var(--font-weight-semibold)',
                            color: 'var(--color-text-primary)'
                        }}>
                            {item.subject || 'No Subject'}
                        </div>
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-sm)',
                        color: 'var(--color-text-secondary)',
                        marginTop: 'var(--spacing-xs)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-sm)'
                    }}>
                        <span>From: {item.sender || 'Unknown'}</span>
                        <span style={{ color: 'var(--color-border)' }}>|</span>
                        <span>{new Date(item.receivedAt).toLocaleString()}</span>
                    </div>
                </div>

                {/* Right Side: Badge & Confidence */}
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-end',
                    gap: 'var(--spacing-xs)',
                    flexShrink: 0
                }}>
                    <span style={getBadgeStyle(item.classification?.classification)}>
                        {item.classification?.classification || 'Unknown'}
                    </span>
                    {item.classification?.confidence && (
                        <span style={{
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--color-text-tertiary)'
                        }}>
                            {formatConfidence(item.classification.confidence)} Confidence
                        </span>
                    )}
                </div>
            </div>

            {/* Content - Always Visible */}
            <div style={{
                padding: '0 var(--spacing-md) var(--spacing-md) var(--spacing-md)',
                borderTop: '1px solid var(--color-border)',
                marginTop: 'var(--spacing-xs)',
                paddingTop: 'var(--spacing-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--spacing-lg)'
            }}>

                {/* Primary Reason */}
                {item.classification?.primary_reason && (
                    <div>
                        <div style={{
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 'var(--font-weight-semibold)',
                            textTransform: 'uppercase',
                            color: 'var(--color-text-tertiary)',
                            marginBottom: 'var(--spacing-xs)',
                            letterSpacing: '0.05em'
                        }}>
                            Analysis
                        </div>
                        <div style={{
                            fontSize: 'var(--font-size-sm)',
                            color: 'var(--color-text-primary)',
                            lineHeight: 'var(--line-height-relaxed)'
                        }}>
                            {item.classification.primary_reason}
                        </div>
                    </div>
                )}

                {/* Evidence / Quotes */}
                {item.classification?.evidence && item.classification.evidence.length > 0 && (
                    <div>
                        <div style={{
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 'var(--font-weight-semibold)',
                            textTransform: 'uppercase',
                            color: 'var(--color-text-tertiary)',
                            marginBottom: 'var(--spacing-xs)',
                            letterSpacing: '0.05em'
                        }}>
                            Key Evidence
                        </div>
                        <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 'var(--spacing-sm)'
                        }}>
                            {item.classification.evidence.map((ev, idx) => (
                                <div key={idx} style={{
                                    padding: 'var(--spacing-sm)',
                                    background: 'var(--color-surface-hover)',
                                    borderRadius: 'var(--radius-sm)',
                                    borderLeft: '2px solid var(--color-primary)',
                                    fontSize: 'var(--font-size-sm)',
                                    color: 'var(--color-text-secondary)',
                                    fontStyle: 'italic'
                                }}>
                                    "{ev.quote}"
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Indicators */}
                {item.classification?.indicators && item.classification.indicators.length > 0 && (
                    <div>
                        <div style={{
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 'var(--font-weight-semibold)',
                            textTransform: 'uppercase',
                            color: 'var(--color-text-tertiary)',
                            marginBottom: 'var(--spacing-xs)',
                            letterSpacing: '0.05em'
                        }}>
                            Indicators
                        </div>
                        <div style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: 'var(--spacing-xs)'
                        }}>
                            {item.classification.indicators.map((indicator, idx) => (
                                <span key={idx} style={{
                                    fontSize: 'var(--font-size-xs)',
                                    padding: '2px 8px',
                                    background: 'var(--color-surface-hover)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--color-text-secondary)',
                                    border: '1px solid var(--color-border)'
                                }}>
                                    {indicator.replace(/_/g, ' ')}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Original Snippet */}
                {item.snippet && (
                    <div>
                        <div style={{
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 'var(--font-weight-semibold)',
                            textTransform: 'uppercase',
                            color: 'var(--color-text-tertiary)',
                            marginBottom: 'var(--spacing-xs)',
                            letterSpacing: '0.05em'
                        }}>
                            Original Email Snippet
                        </div>
                        <div style={{
                            fontSize: 'var(--font-size-sm)',
                            color: 'var(--color-text-tertiary)',
                            fontFamily: 'monospace',
                            background: 'var(--color-background)',
                            padding: 'var(--spacing-sm)',
                            borderRadius: 'var(--radius-sm)'
                        }}>
                            {item.snippet}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default ClassificationItem
