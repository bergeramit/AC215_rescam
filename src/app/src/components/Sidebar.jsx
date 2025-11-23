import { useLocation } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

function Sidebar() {
  const location = useLocation()

  const menuItems = [
    {
      id: 'inbox',
      label: 'Inbox',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
          <polyline points="22,6 12,13 2,6"></polyline>
        </svg>
      ),
      path: '/'
    },
    {
      id: 'classifications',
      label: 'Classifications',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11l3 3L22 4"></path>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        </svg>
      ),
      path: '/classifications'
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M12 1v6m0 6v6m9-9h-6m-6 0H3m15.364 6.364l-4.243-4.243m-4.242 0L5.636 18.364M18.364 5.636l-4.243 4.243m-4.242 0L5.636 5.636"></path>
        </svg>
      ),
      path: '/settings'
    }
  ]

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside className="sidebar">
      {/* Logo Section */}
      <div style={{
        padding: 'var(--spacing-lg)',
        borderBottom: '1px solid var(--color-sidebar-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{
          fontSize: 'var(--font-size-xl)',
          fontWeight: 'var(--font-weight-bold)',
          color: 'var(--color-text-primary)',
          letterSpacing: '-0.5px'
        }}>
          Rescam
        </div>
        <ThemeToggle />
      </div>

      {/* Navigation Items */}
      <nav style={{
        flex: 1,
        padding: 'var(--spacing-md) 0',
        overflowY: 'auto'
      }}>
        {menuItems.map((item) => (
          <div
            key={item.id}
            className={`sidebar-item ${isActive(item.path) ? 'active' : ''}`}
            onClick={() => {
              // For now, just handle inbox (home)
              if (item.path === '/') {
                window.location.hash = ''
              }
            }}
          >
            <div className="sidebar-item-icon">
              {item.icon}
            </div>
            <span className="sidebar-item-text">{item.label}</span>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div style={{
        padding: 'var(--spacing-md) var(--spacing-lg)',
        borderTop: '1px solid var(--color-sidebar-border)',
        fontSize: 'var(--font-size-xs)',
        color: 'var(--color-text-tertiary)'
      }}>
        <div style={{ marginBottom: 'var(--spacing-xs)' }}>
          Enterprise Email Security
        </div>
        <div style={{ fontSize: '10px' }}>
          v1.0.0
        </div>
      </div>
    </aside>
  )
}

export default Sidebar

