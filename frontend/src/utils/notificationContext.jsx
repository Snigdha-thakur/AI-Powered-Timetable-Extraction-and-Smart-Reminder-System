import React, { createContext, useState, useCallback } from 'react'

export const NotificationContext = createContext()

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([])

  const add = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now()
    setNotifications(prev => [...prev, { id, message, type }])
    if (duration) {
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== id))
      }, duration)
    }
    return id
  }, [])

  const remove = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  return (
    <NotificationContext.Provider value={{ add, remove }}>
      {children}
      <ToastContainer notifications={notifications} onRemove={remove} />
    </NotificationContext.Provider>
  )
}

function ToastContainer({ notifications, onRemove }) {
  return (
    <div style={styles.container}>
      {notifications.map(n => (
        <Toast key={n.id} notification={n} onRemove={onRemove} />
      ))}
    </div>
  )
}

function Toast({ notification, onRemove }) {
  const typeStyles = {
    success: { bg: '#dcfce7', color: '#166534', icon: '✓' },
    error: { bg: '#fee2e2', color: '#991b1b', icon: '✕' },
    warning: { bg: '#fef3c7', color: '#92400e', icon: '⚠' },
    info: { bg: '#dbeafe', color: '#0c4a6e', icon: 'ℹ' },
  }
  const style = typeStyles[notification.type] || typeStyles.info

  React.useEffect(() => {
    const timer = setTimeout(() => onRemove(notification.id), 4000)
    return () => clearTimeout(timer)
  }, [notification.id, onRemove])

  return (
    <div style={{...styles.toast, background: style.bg, color: style.color}}>
      <span style={{marginRight: '8px'}}>{style.icon}</span>
      {notification.message}
      <button onClick={() => onRemove(notification.id)} style={styles.closeBtn}>✕</button>
    </div>
  )
}

const styles = {
  container: {
    position: 'fixed',
    top: '20px',
    right: '20px',
    zIndex: 9999,
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    maxWidth: '400px',
  },
  toast: {
    padding: '12px 16px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.9rem',
    fontWeight: '500',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    animation: 'slideIn 0.3s ease-out',
  },
  closeBtn: {
    marginLeft: '12px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '0',
    fontSize: '1.2rem',
    opacity: 0.7,
  }
}
