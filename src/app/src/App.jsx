import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import { getStoredUser } from './auth/googleAuth'
import './styles/global.css'

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const location = useLocation()

  const checkAuth = () => {
    const user = getStoredUser()
    setIsAuthenticated(!!user)
    setLoading(false)
  }

  useEffect(() => {
    checkAuth()
    // Initialize theme
    const savedTheme = localStorage.getItem('rescam-theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  // Re-check auth when route changes (in case user just signed in)
  useEffect(() => {
    checkAuth()
  }, [location])

  // Listen for storage changes (when auth data is stored)
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'google_user' || e.key === 'google_access_token') {
        checkAuth()
      }
    }
    window.addEventListener('storage', handleStorageChange)
    // Also listen for same-tab storage changes via custom event
    window.addEventListener('auth-storage-change', checkAuth)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('auth-storage-change', checkAuth)
    }
  }, [])

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        color: 'var(--color-text-secondary)',
        fontSize: 'var(--font-size-base)'
      }}>
        Loading...
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Dashboard /> : <Login />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
