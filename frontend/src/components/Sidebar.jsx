import React from 'react'
import { NavLink } from 'react-router-dom'
import styles from './Sidebar.module.css'

const navItems = [
  { to: '/dashboard/profile',   icon: '👤', label: 'Profile' },
  { to: '/dashboard/upload',    icon: '🖼️', label: 'Image Upload' },
  { to: '/dashboard/classes',   icon: '📚', label: 'My Classes' },
  { to: '/dashboard/calendar',  icon: '📅', label: 'Academic Calendar' },
  { to: '/dashboard/settings',  icon: '⚙️', label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `${styles.item} ${isActive ? styles.active : ''}`}
          >
            <span className={styles.icon}>{icon}</span>
            <span className={styles.label}>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
