import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme, useToast } from '../../utils/hooks'
import styles from './Section.module.css'

export default function Settings() {
  const navigate = useNavigate()
  const { isDark, toggleTheme } = useTheme()
  const toast = useToast()
  const [notifications, setNotifications] = useState(true)
  const [reminderTime, setReminderTime] = useState('15')
  const [semesterStart, setSemesterStart] = useState(localStorage.getItem('semester_start') || '2026-01-15')
  const [semesterEnd, setSemesterEnd] = useState(localStorage.getItem('semester_end') || '2026-05-31')
  const [saving, setSaving] = useState(false)

  const saveSemesterDates = async () => {
    setSaving(true)
    try {
      localStorage.setItem('semester_start', semesterStart)
      localStorage.setItem('semester_end', semesterEnd)
      localStorage.setItem('reminder_time', reminderTime)
      localStorage.setItem('notifications_enabled', notifications)
      toast.success('✓ Settings saved successfully')
    } catch (err) {
      toast.error(`✕ ${err.message}`)
    } finally { setSaving(false) }
  }

  const logout = () => {
    localStorage.clear()
    toast.info('👋 Logged out')
    navigate('/')
  }

  const exportData = () => {
    const data = {
      semester: { start: semesterStart, end: semesterEnd },
      timetable_id: localStorage.getItem('timetable_id'),
      theme: isDark ? 'dark' : 'light',
      timestamp: new Date().toISOString()
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'timetable-settings.json'
    a.click()
    toast.success('✓ Settings exported')
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.title}>⚙️ Settings</h2>
      <div className={styles.card}>

        {/* Semester Dates */}
        <div className={styles.settingsBlock}>
          <h3 className={styles.settingsBlockTitle}>📅 Semester Dates</h3>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
            <div className={styles.field}>
              <label>Start Date</label>
              <input type="date" value={semesterStart} onChange={e => setSemesterStart(e.target.value)} className={styles.inlineInput} />
            </div>
            <div className={styles.field}>
              <label>End Date</label>
              <input type="date" value={semesterEnd} onChange={e => setSemesterEnd(e.target.value)} className={styles.inlineInput} />
            </div>
          </div>
          <div className={styles.settingsHint}>
            📝 These dates are used for calendar view and Google Calendar sync
          </div>
        </div>

        {/* Notifications */}
        <div className={styles.settingsBlock}>
          <div className={styles.settingRow}>
            <div>
              <div className={styles.settingLabel}>Email Notifications</div>
              <div className={styles.settingDesc}>Receive class reminders via email</div>
            </div>
            <label className={styles.toggle}>
              <input type="checkbox" checked={notifications} onChange={e => setNotifications(e.target.checked)} />
              <span className={styles.slider}></span>
            </label>
          </div>
          <div className={styles.settingRow}>
            <div>
              <div className={styles.settingLabel}>Reminder Time</div>
              <div className={styles.settingDesc}>Minutes before class starts</div>
            </div>
            <select className={styles.select} value={reminderTime} onChange={e => setReminderTime(e.target.value)}>
              <option value="5">5 minutes</option>
              <option value="15">15 minutes</option>
              <option value="30">30 minutes</option>
              <option value="60">1 hour</option>
            </select>
          </div>
        </div>

        {/* Theme */}
        <div className={styles.settingsBlock}>
          <div className={styles.settingRow}>
            <div>
              <div className={styles.settingLabel}>Dark Mode</div>
              <div className={styles.settingDesc}>{isDark ? 'Enabled' : 'Disabled'}</div>
            </div>
            <label className={styles.toggle}>
              <input type="checkbox" checked={isDark} onChange={toggleTheme} />
              <span className={styles.slider}></span>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className={styles.settingsBlock}>
          <h3 className={styles.settingsBlockTitle}>Actions</h3>
          <button className={styles.primaryBtn} onClick={saveSemesterDates} disabled={saving}>
            {saving ? <><span className={styles.btnSpinner}/> Saving…</> : '💾 Save Settings'}
          </button>
          <button className={styles.outlineBtn}
            style={{width: '100%', marginTop: '8px', padding: '10px 16px'}}
            onClick={exportData}>
            📥 Export Settings
          </button>
        </div>

        <button className={styles.dangerBtn} onClick={logout}>🚪 Logout</button>
      </div>
    </div>
  )
}
