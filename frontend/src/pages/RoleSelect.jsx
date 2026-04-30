import React from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './RoleSelect.module.css'

const roles = [
  {
    key: 'student',
    label: 'Student',
    icon: (
      <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="72" height="72">
        <circle cx="40" cy="22" r="13" stroke="#415E72" strokeWidth="4" fill="none" />
        <path d="M17 64c0-12.703 10.297-23 23-23s23 10.297 23 23" stroke="#415E72" strokeWidth="4" strokeLinecap="round" fill="none" />
        <rect x="25" y="52" width="30" height="16" rx="3" stroke="#415E72" strokeWidth="3" fill="none" />
        <path d="M29 57h22M29 62h14" stroke="#415E72" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    key: 'faculty',
    label: 'Faculty',
    icon: (
      <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="72" height="72">
        <rect x="10" y="30" width="60" height="36" rx="7" fill="#415E72" />
        <path d="M27 30v-9a13 13 0 0126 0v9" stroke="#415E72" strokeWidth="4" strokeLinecap="round" fill="none" />
        <rect x="31" y="42" width="18" height="13" rx="3" fill="#F3E2D4" />
        <circle cx="40" cy="48.5" r="2.5" fill="#415E72" />
      </svg>
    ),
  },
  {
    key: 'phd',
    label: 'PHD Scholar',
    icon: (
      <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="72" height="72">
        <path d="M8 38L40 20l32 18-32 18L8 38z" fill="#C5B0CD" />
        <path d="M40 56v10" stroke="#415E72" strokeWidth="4" strokeLinecap="round" />
        <path d="M28 66h24" stroke="#415E72" strokeWidth="4" strokeLinecap="round" />
        <path d="M64 38v14" stroke="#C5B0CD" strokeWidth="3.5" strokeLinecap="round" />
        <circle cx="64" cy="54" r="3.5" fill="#C5B0CD" />
      </svg>
    ),
  },
]

export default function RoleSelect() {
  const navigate = useNavigate()

  const handleRole = (role) => {
    sessionStorage.setItem('role', role)
    navigate('/auth')
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Timetable OCR &amp; Reminders</h1>
      <p className={styles.subtitle}>Continue as</p>
      <div className={styles.cards}>
        {roles.map((r) => (
          <div key={r.key} className={styles.cardWrap} onClick={() => handleRole(r.key)}>
            <div className={styles.card}>{r.icon}</div>
            <span className={styles.label}>{r.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
