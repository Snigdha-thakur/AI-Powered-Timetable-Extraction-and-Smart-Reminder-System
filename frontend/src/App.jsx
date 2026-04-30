import React, { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useToast } from './utils/hooks'
import RoleSelect from './pages/RoleSelect'
import AuthPage from './pages/AuthPage'
import Dashboard from './pages/Dashboard'

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/auth" replace />
}

export default function App() {
  const location = useLocation()
  const toast = useToast()

  useEffect(() => {
    // Handle Google Calendar sync callback
    const params = new URLSearchParams(location.search)
    if (params.has('calendar_sync')) {
      const status = params.get('calendar_sync')
      const events = params.get('events')
      if (status === 'success') {
        toast.success(`✓ ${events} events synced to Google Calendar`)
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname)
      } else if (status === 'error') {
        toast.error(`✕ Failed to sync with Google Calendar`)
        window.history.replaceState({}, document.title, window.location.pathname)
      }
    }
  }, [location.search, toast])

  return (
    <Routes>
      <Route path="/"           element={<RoleSelect />} />
      <Route path="/auth"       element={<AuthPage />} />
      <Route path="/dashboard/*" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="*"           element={<Navigate to="/" replace />} />
    </Routes>
  )
}
