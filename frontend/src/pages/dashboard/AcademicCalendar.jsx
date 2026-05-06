import React, { useState, useMemo } from 'react'
import { api } from '../../api'
import { useToast } from '../../utils/hooks'
import styles from './Section.module.css'

export default function AcademicCalendar() {
  const [timetable, setTimetable] = useState(null)
  const [inputId, setInputId]     = useState(localStorage.getItem('timetable_id') || '')
  const [startDate, setStartDate] = useState(localStorage.getItem('semester_start') || '2026-01-15')
  const [endDate, setEndDate]     = useState(localStorage.getItem('semester_end') || '2026-05-31')
  const [events, setEvents]       = useState([])
  const [loading, setLoading]     = useState(false)
  const [syncing, setSyncing]     = useState(false)
  const [removing, setRemoving]   = useState(false)
  const toast = useToast()

  const fetchCalendarView = async (id, sd, ed) => {
    if (!id || !sd || !ed) return
    setLoading(true)
    try {
      const data = await api.get(`/timetable/${id}/calendar-view?start_date=${sd}&end_date=${ed}`)
      setEvents(data.events || [])
      setTimetable(data)
      localStorage.setItem('timetable_id', id)
      localStorage.setItem('semester_start', sd)
      localStorage.setItem('semester_end', ed)
      toast.success(`✓ Calendar loaded (${data.events.length} events)`)
    } catch (err) {
      toast.error(`✕ ${err.message}`)
    } finally { setLoading(false) }
  }

  const handleSync = async () => {
    if (!inputId || !startDate || !endDate || !timetable) {
      toast.error('✕ Missing required fields')
      return
    }
    setSyncing(true)
    try {
      const url = `http://127.0.0.1:8000/timetable/${inputId}/add-to-google-calendar?start_date=${startDate}&end_date=${endDate}`
      toast.success('🔄 Redirecting to Google Calendar...')
      window.location.href = url
    } catch (err) {
      toast.error(`✕ ${err.message}`)
      setSyncing(false)
    }
  }

  const handleRemove = async () => {
    if (!inputId) { toast.error('✕ No timetable loaded'); return }
    if (!startDate || !endDate) { toast.error('✕ Set semester dates first'); return }
    setRemoving(true)
    try {
      const { auth_url } = await api.delete(`/timetable/${inputId}/remove-from-google-calendar?start_date=${startDate}&end_date=${endDate}`)
      toast.success('🔄 Redirecting to Google...')
      window.location.href = auth_url
    } catch (err) {
      toast.error(`✕ ${err.message}`)
      setRemoving(false)
    }
  }

  const eventsByDate = useMemo(() => {
    const grouped = {}
    events.forEach(e => {
      if (!grouped[e.date]) grouped[e.date] = []
      grouped[e.date].push(e)
    })
    return grouped
  }, [events])

  return (
    <div className={styles.section}>
      <h2 className={styles.title}>📅 Academic Calendar</h2>
      <div className={styles.card}>

        <div className={styles.form}>
          <div>
            <label className={styles.fieldLabel}>Timetable ID</label>
            <input className={styles.inlineInput} value={inputId}
              onChange={e => setInputId(e.target.value)}
              placeholder="TT-A1B2C3" />
          </div>

          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
            <div>
              <label className={styles.fieldLabel}>Semester Start</label>
              <input type="date" className={styles.inlineInput} value={startDate}
                onChange={e => setStartDate(e.target.value)} />
            </div>
            <div>
              <label className={styles.fieldLabel}>Semester End</label>
              <input type="date" className={styles.inlineInput} value={endDate}
                onChange={e => setEndDate(e.target.value)} />
            </div>
          </div>

          <div style={{display: 'flex', gap: '10px', flexWrap: 'wrap'}}>
            <button className={styles.primaryBtn}
              style={{flex: 1, minWidth: '160px'}}
              onClick={() => fetchCalendarView(inputId, startDate, endDate)}
              disabled={loading || !inputId}>
              {loading ? <><span className={styles.btnSpinner}/> Loading…</> : '📅 Load Calendar'}
            </button>
            <button className={styles.outlineBtn}
              style={{flex: 1, minWidth: '160px', padding: '10px 16px'}}
              onClick={handleSync}
              disabled={!timetable || !inputId || syncing}>
              {syncing ? '🔄 Syncing…' : '🔗 Add to Google Calendar'}
            </button>
            <button className={styles.dangerBtn}
              style={{flex: 1, minWidth: '160px', padding: '10px 16px'}}
              onClick={handleRemove}
              disabled={!inputId || removing}>
              {removing ? '🔄 Removing…' : '🗑️ Remove from Google Calendar'}
            </button>
          </div>
        </div>

        {timetable && (
          <>
            <div className={styles.calendarSummary}>
              📊 {events.length} events from {startDate} to {endDate}
            </div>
            <EventsTimeline events={eventsByDate} totalDates={Object.keys(eventsByDate).length} />
          </>
        )}
      </div>
    </div>
  )
}

function EventsTimeline({ events, totalDates }) {
  const sortedDates = Object.keys(events).sort()

  if (sortedDates.length === 0) {
    return <div className="calEmpty">No events in this date range</div>
  }

  return (
    <div style={{marginTop: '20px'}}>
      <h3 className="calTimelineTitle">📍 Events Timeline</h3>
      <div className="calTimeline">
        {sortedDates.slice(0, 20).map(date => (
          <EventDateGroup key={date} date={date} events={events[date]} />
        ))}
      </div>
      {totalDates > 20 && (
        <div className="calMore">+{totalDates - 20} more dates</div>
      )}
    </div>
  )
}

function EventDateGroup({ date, events }) {
  const dateObj = new Date(date + 'T00:00:00')
  const dateStr = dateObj.toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric'})

  return (
    <div className="calDateGroup">
      <div className="calDateLabel">{dateStr}</div>
      <div style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
        {events.map((e, i) => <EventCard key={i} event={e} />)}
      </div>
    </div>
  )
}

function EventCard({ event }) {
  return (
    <div className="calEventCard">
      <div>
        <div className="calEventSubject">{event.course_code}</div>
        <div className="calEventMeta">
          {event.time_start}{event.venue ? ` • ${event.venue}` : ''}
        </div>
      </div>
      <span className={`calEventBadge ${event.type === 'LAB' ? 'calEventBadgeLab' : 'calEventBadgeTheory'}`}>
        {event.type}
      </span>
    </div>
  )
}
