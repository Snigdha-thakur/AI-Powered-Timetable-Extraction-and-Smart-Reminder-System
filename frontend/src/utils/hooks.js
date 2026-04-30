import { useContext, useState } from 'react'
import { NotificationContext } from './notificationContext'

export function useNotification() {
  const context = useContext(NotificationContext)
  if (!context) {
    // Fallback if used outside provider (shouldn't happen in this app)
    return {
      add: (msg, type, duration) => {
        console.log(`[${type}] ${msg}`)
      },
      remove: () => {}
    }
  }
  return context
}

export function useToast() {
  const { add } = useNotification()
  return {
    success: (msg, duration) => add(msg, 'success', duration || 3000),
    error: (msg, duration) => add(msg, 'error', duration || 4000),
    warning: (msg, duration) => add(msg, 'warning', duration || 4000),
    info: (msg, duration) => add(msg, 'info', duration || 3000),
  }
}

// Dark mode hook
export function useTheme() {
  const [isDark, setIsDark] = useState(
    () => localStorage.getItem('theme') === 'dark'
  )

  const toggleTheme = () => {
    const newTheme = isDark ? 'light' : 'dark'
    localStorage.setItem('theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
    setIsDark(!isDark)
  }

  return { isDark, toggleTheme }
}
