import React, { useState, useEffect } from 'react'
import { api } from '../../api'
import { useToast } from '../../utils/hooks'
import styles from './Section.module.css'

export default function Profile() {
  const role = sessionStorage.getItem('role') || 'student'
  const isFaculty = role === 'faculty'

  const [profile, setProfile] = useState(null)
  const [form, setForm]       = useState({ full_name: '', registration_number: '', employee_id: '', phone: '', department: '', degree: '', sem: '' })
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)
  const toast = useToast()

  useEffect(() => {
    api.get('/auth/profile')
      .then(d => {
        setProfile(d)
        setForm({
          full_name:           d.full_name           || '',
          registration_number: d.registration_number || '',
          employee_id:         d.employee_id         || '',
          phone:               d.phone               || '',
          department:          d.department          || '',
          degree:              d.degree              || '',
          sem:                 d.sem                 || '',
        })
      })
      .catch(e => toast.error(`✕ Failed to load profile: ${e.message}`))
      .finally(() => setFetching(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const save = async (e) => {
    e.preventDefault(); setLoading(true)
    try {
      const d = await api.post('/auth/profile/setup', { ...form, role })
      setProfile(d.profile)
      toast.success('✓ Profile updated successfully!')
    } catch (err) {
      toast.error(`✕ ${err.message}`)
    }
    finally { setLoading(false) }
  }

  if (fetching) return (
    <div className={styles.section}>
      <h2 className={styles.title}>👤 Profile</h2>
      <div className={styles.card}><div className={styles.loadingRow}>Loading profile…</div></div>
    </div>
  )

  return (
    <div className={styles.section}>
      <h2 className={styles.title}>👤 Profile</h2>
      <div className={styles.card}>
        {profile && (
          <div className={styles.profileHeader}>
            <div className={styles.bigAvatar}>{(profile.email || 'U')[0].toUpperCase()}</div>
            <div>
              <div className={styles.profileName}>{profile.full_name || 'Set your name'}</div>
              <div className={styles.profileEmail}>{profile.email || profile.phone}</div>
              {isFaculty
                ? profile.employee_id && <div className={styles.profileReg}>{profile.employee_id}</div>
                : profile.registration_number && <div className={styles.profileReg}>{profile.registration_number}</div>
              }
              {profile.department && (
                <div className={styles.profileMeta}>
                  {profile.department}{!isFaculty && profile.degree ? ` · ${profile.degree}` : ''} · {profile.sem}
                </div>
              )}
            </div>
          </div>
        )}

        <form onSubmit={save} className={styles.form}>
          <div className={styles.grid2}>
            <div className={styles.field}>
              <label>Full Name</label>
              <input value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} placeholder="Your full name" />
            </div>
            <div className={styles.field}>
              <label>{isFaculty ? 'Employee ID' : 'Registration No.'}</label>
              {isFaculty
                ? <input value={form.employee_id} onChange={e => setForm({...form, employee_id: e.target.value})} placeholder="EMP12345" />
                : <input value={form.registration_number} onChange={e => setForm({...form, registration_number: e.target.value})} placeholder="22BCE8076" />
              }
            </div>
            <div className={styles.field}>
              <label>Phone</label>
              <input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} placeholder="9876543210" />
            </div>
            <div className={styles.field}>
              <label>Department</label>
              <input value={form.department} onChange={e => setForm({...form, department: e.target.value})} placeholder="Scope" />
            </div>
            {!isFaculty && (
              <div className={styles.field}>
                <label>Degree</label>
                <input value={form.degree} onChange={e => setForm({...form, degree: e.target.value})} placeholder="BTech" />
              </div>
            )}
            <div className={styles.field}>
              <label>Semester</label>
              <input value={form.sem} onChange={e => setForm({...form, sem: e.target.value})} placeholder="Fall Sem 2026-2027" />
            </div>
          </div>
          <button type="submit" className={styles.primaryBtn} disabled={loading}>
            {loading ? <><span className={styles.btnSpinner}/>Saving…</> : '💾 Save Profile'}
          </button>
        </form>
      </div>
    </div>
  )
}
