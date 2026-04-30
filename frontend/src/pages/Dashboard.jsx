import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import TopNav from '../components/TopNav'
import Sidebar from '../components/Sidebar'
import Profile from './dashboard/Profile'
import ImageUpload from './dashboard/ImageUpload'
import MyClasses from './dashboard/MyClasses'
import AcademicCalendar from './dashboard/AcademicCalendar'
import Settings from './dashboard/Settings'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  return (
    <div className={styles.layout}>
      <TopNav />
      <Sidebar />
      <main className={styles.main}>
        <Routes>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile"  element={<Profile />} />
          <Route path="upload"   element={<ImageUpload />} />
          <Route path="classes"  element={<MyClasses />} />
          <Route path="calendar" element={<AcademicCalendar />} />
          <Route path="settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
