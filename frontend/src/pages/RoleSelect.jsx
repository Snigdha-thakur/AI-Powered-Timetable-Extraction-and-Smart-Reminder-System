import React from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './RoleSelect.module.css'

export default function RoleSelect() {
  const navigate = useNavigate()

  const handleLogin = () => {
    sessionStorage.setItem('role', 'student')
    navigate('/auth')
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Timetable OCR &amp; Reminders</h1>
      <p className={styles.subtitle}>Continue as</p>
      <div className={styles.cards}>
        <div className={styles.cardWrap} onClick={handleLogin}>
          <div className={styles.card}>
            <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="72" height="72">
              <circle cx="40" cy="22" r="13" stroke="#415E72" strokeWidth="4" fill="none" />
              <path d="M17 64c0-12.703 10.297-23 23-23s23 10.297 23 23" stroke="#415E72" strokeWidth="4" strokeLinecap="round" fill="none" />
              <rect x="25" y="52" width="30" height="16" rx="3" stroke="#415E72" strokeWidth="3" fill="none" />
              <path d="M29 57h22M29 62h14" stroke="#415E72" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <span className={styles.label}>Student</span>
        </div>
      </div>
    </div>
  )
}
