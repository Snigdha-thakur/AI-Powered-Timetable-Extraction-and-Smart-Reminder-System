import React, { useState, useEffect } from 'react'
import { api } from '../../api'
import { useToast } from '../../utils/hooks'
import styles from './Section.module.css'

const DAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
const TODAY = DAY_ORDER[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1]

export default function MyClasses() {
  const [timetable, setTimetable]   = useState(null)
  const [activeDay, setActiveDay]   = useState(null)
  const [loading, setLoading]       = useState(false)
  const [reminder, setReminder]     = useState(null)
  const [remLoading, setRemLoading] = useState(false)
  const toast = useToast()

  const loadTimetable = (data, id) => {
    setTimetable(data)
    localStorage.setItem('timetable_id', id)
    // Default to today if classes exist, else first available day
    const todayHasClasses = data[TODAY]?.length > 0
    const firstDay = DAY_ORDER.find(d => data[d]?.length > 0)
    setActiveDay(todayHasClasses ? TODAY : (firstDay || Object.keys(data)[0] || 'Monday'))
  }

  useEffect(() => {
    setLoading(true)
    api.get('/timetable/my')
      .then(res => { loadTimetable(res.data, res.timetable_id); toast.success('✓ Timetable loaded') })
      .catch(() => {
        // fallback to cached id
        const id = localStorage.getItem('timetable_id')
        if (id) {
          api.get(`/timetable/${id}`)
            .then(data => { loadTimetable(data, id); toast.success('✓ Timetable loaded') })
            .catch(err => toast.error(`✕ ${err.message}`))
            .finally(() => setLoading(false))
        } else {
          setLoading(false)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  const createReminder = async () => {
    if (!reminder) return
    setRemLoading(true)
    try {
      const ttId = localStorage.getItem('timetable_id')
      await api.post('/reminder', {
        timetable_id: ttId,
        day: reminder.day,
        time: reminder.time.split('-')[0].trim(),
        subject: reminder.course_code,
        faculty: '',
        venue: reminder.venue || '',
      })
      toast.success(`✓ Reminder set for ${reminder.course_code}`)
      setReminder(null)
    } catch (err) {
      toast.error(`✕ ${err.message}`)
    }
    finally { setRemLoading(false) }
  }

  // Only show days present in the response, sorted by DAY_ORDER
  const availableDays = timetable
    ? DAY_ORDER.filter(d => timetable[d])
    : []

  const classes = (timetable && activeDay ? timetable[activeDay] : []) || []
  // Sort classes by time
  const sortedClasses = [...classes].sort((a, b) => a.time.localeCompare(b.time))

  return (
    <div className={styles.section}>
      <h2 className={styles.title}>📚 My Classes</h2>

      <div className={styles.card}>
        {loading && <div className={styles.progressBar}><div className={styles.progressFill} style={{width: '60%'}}></div></div>}
        {!timetable && !loading && (
          <p className={styles.empty}>No timetable found. Upload one from <strong>Upload Timetable</strong>.</p>
        )}

        {timetable && (
          <>
            <div className={styles.dayTabs}>
              {availableDays.map(d => (
                <button key={d}
                  className={`${styles.dayTab} ${activeDay === d ? styles.activeDayTab : ''} ${d === TODAY && activeDay !== d ? styles.todayTab : ''}`}
                  onClick={() => setActiveDay(d)}>
                  {d.slice(0, 3)}{d === TODAY ? ' 📍' : ''}
                  <span className={styles.dayCount}>{timetable[d].length}</span>
                </button>
              ))}
            </div>

            {sortedClasses.length === 0
              ? <p className={styles.empty}>No classes scheduled on {activeDay}</p>
              : (
                <div className={styles.classList}>
                  {sortedClasses.map((c, i) => (
                    <div key={i} className={`${styles.classCard} ${c.type === 'LAB' ? styles.labCard : ''}`}>
                      <div className={styles.classTime}>{c.time}</div>
                      <div className={styles.classInfo}>
                        <div className={styles.classSubject}>{c.course_code}</div>
                        <div className={styles.classFaculty}>{c.slot}</div>
                        {c.venue && <div className={styles.classVenue}>📍 {c.venue}</div>}
                      </div>
                      <span className={`${styles.typeBadge} ${c.type === 'LAB' ? styles.labBadge : styles.theoryBadge}`}>
                        {c.type}
                      </span>
                      <button className={styles.remBtn}
                        title="Set reminder"
                        onClick={() => setReminder({ ...c, day: activeDay })}>
                        🔔
                      </button>
                    </div>
                  ))}
                </div>
              )
            }
          </>
        )}

        {reminder && (
          <div className={styles.reminderPanel}>
            <div className={styles.reminderTitle}>🔔 Set Reminder</div>
            <div className={styles.reminderDetail}>
              <strong>{reminder.course_code}</strong> · {reminder.day} · {reminder.time}
            </div>
            <div className={styles.reminderDetail}>Slot: {reminder.slot} · {reminder.type}</div>
            {reminder.venue && <div className={styles.reminderDetail}>📍 {reminder.venue}</div>}
            <div className={styles.reminderActions}>
              <button className={styles.primaryBtn}
                style={{ width: 'auto', padding: '9px 20px' }}
                onClick={createReminder} disabled={remLoading}>
                {remLoading ? <span className={styles.btnSpinner}/> : null}
                {remLoading ? 'Setting…' : 'Confirm Reminder'}
              </button>
              <button className={styles.outlineBtn} onClick={() => setReminder(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
