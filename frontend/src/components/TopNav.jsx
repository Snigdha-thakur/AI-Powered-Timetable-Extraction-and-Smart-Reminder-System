import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../utils/hooks'
import styles from './TopNav.module.css'

export default function TopNav() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const { isDark, toggleTheme } = useTheme()
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  const logout = () => {
    localStorage.clear()
    navigate('/')
  }

  return (
    <header className={styles.topnav}>
      <div className={styles.logo}>
        <span className={styles.logoIcon}>🗓</span>
        <span className={styles.logoText}>TimeTable<span className={styles.logoAccent}>OCR</span></span>
      </div>

      <div className={styles.right}>
        <span className={styles.badge}>{sessionStorage.getItem('role') || 'Student'}</span>
        
        <button className={styles.themeToggle} onClick={toggleTheme} title="Toggle dark mode">
          {isDark ? '☀️' : '🌙'}
        </button>

        <div className={styles.profileWrap} onClick={() => setMenuOpen(!menuOpen)}>
          <div className={styles.avatar}>
            {(user.email || 'U')[0].toUpperCase()}
          </div>
          <span className={styles.userName}>{user.email?.split('@')[0] || 'User'}</span>
          <span className={styles.chevron}>▾</span>
          {menuOpen && (
            <div className={styles.dropdown}>
              <div className={styles.dropItem} onClick={() => navigate('/dashboard/profile')}>👤 Profile</div>
              <div className={styles.dropItem} onClick={() => navigate('/dashboard/settings')}>⚙️ Settings</div>
              <div className={`${styles.dropItem} ${styles.logoutItem}`} onClick={logout}>🚪 Logout</div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
