import React, { useState, useRef } from 'react'
import { api } from '../../api'
import { useToast } from '../../utils/hooks'
import styles from './Section.module.css'

export default function ImageUpload() {
  const [schedFile, setSchedFile] = useState(null)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [drag, setDrag]           = useState(false)
  const [progress, setProgress]   = useState(0)
  const toast = useToast()
  const schedRef = useRef()

  const reset = () => { setResult(null); setError(''); setProgress(0) }

  const handleImageUpload = async (e) => {
    e.preventDefault(); reset(); setLoading(true); setProgress(10)
    try {
      if (!schedFile) throw new Error('Please select a schedule image')
      setProgress(25)
      const form = new FormData()
      form.append('schedule_image', schedFile)
      setProgress(50)
      const data = await api.postForm('/upload-schedule', form)
      setProgress(90)
      setResult(data)
      localStorage.setItem('timetable_id', data.timetable_id)
      setProgress(100)
      toast.success(`✓ Timetable extracted! ID: ${data.timetable_id}`)
    } catch (err) {
      const msg = err.message || 'Upload failed'
      setError(msg)
      toast.error(`✕ ${msg}`)
    }
    finally { setLoading(false); setProgress(0) }
  }

  const onDrop = (e) => {
    e.preventDefault(); setDrag(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      if (file.type.startsWith('image/')) {
        setSchedFile(file)
        toast.info('✓ Image ready to upload')
      } else {
        toast.error('✕ Please drop an image file')
      }
    }
  }

  const FileDropZone = ({ file, setFile, inputRef }) => (
    <div
      className={`${styles.fileZone} ${drag ? styles.dragOver : ''} ${file ? styles.fileZoneFilled : ''}`}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current.click()}
    >
      <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }}
        onChange={e => {
          const f = e.target.files[0]
          if (f) {
            setFile(f)
            toast.info('✓ Image selected')
          }
        }} />
      {file ? (
        <div className={styles.fileChosen}>
          <span className={styles.fileIcon}>🖼️</span>
          <div>
            <div className={styles.fileName}>{file.name}</div>
            <div className={styles.fileSize}>{(file.size / 1024).toFixed(1)} KB</div>
          </div>
          <button type="button" className={styles.fileRemove}
            onClick={e => { e.stopPropagation(); setFile(null); toast.info('Image removed') }}>✕</button>
        </div>
      ) : (
        <>
          <div className={styles.dropIcon}>📁</div>
          <div className={styles.dropText}>Schedule Image</div>
          <div className={styles.dropSub}>Click or drag & drop an image</div>
        </>
      )}
    </div>
  )

  return (
    <div className={styles.section}>
      <h2 className={styles.title}>🖼️ Upload Timetable</h2>
      <div className={styles.card}>
        {loading && <div className={styles.progressBar}><div className={styles.progressFill} style={{width: `${progress}%`}}></div></div>}
        <form onSubmit={handleImageUpload} className={styles.form}>
          <p className={styles.uploadHint}>
            Upload your <strong>VTOP schedule grid screenshot</strong>.
            Our OCR engine will extract and parse your timetable automatically.
          </p>
          <FileDropZone file={schedFile} setFile={setSchedFile} inputRef={schedRef} />
          {error  && <div className={styles.error}>⚠️ {error}</div>}
          {result && <SuccessBox result={result} />}
          <button type="submit" className={styles.primaryBtn} disabled={loading || !schedFile}>
            {loading ? <><span className={styles.btnSpinner}/>Processing OCR…</> : '🚀 Extract & Upload Timetable'}
          </button>
        </form>
      </div>
    </div>
  )
}

function SuccessBox({ result }) {
  return (
    <div className={styles.successBox}>
      <div className={styles.successIcon}>✅</div>
      <div>
        <div className={styles.successTitle}>Timetable stored successfully!</div>
        <div className={styles.successId}>
          ID: <strong>{result.timetable_id}</strong>
          <button className={styles.copyBtn}
            onClick={() => navigator.clipboard.writeText(result.timetable_id)}>
            📋 Copy
          </button>
        </div>
        <div className={styles.successSub}>Go to <strong>My Classes</strong> to view your schedule.</div>
      </div>
    </div>
  )
}
