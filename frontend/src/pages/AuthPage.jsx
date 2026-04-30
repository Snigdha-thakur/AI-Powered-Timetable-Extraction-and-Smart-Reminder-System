import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import styles from './AuthPage.module.css'

// ── step machine ──────────────────────────────────────────────
// signin | signup_init | signup_otp | signup_pass | forgot_init | forgot_otp | forgot_pass
// ─────────────────────────────────────────────────────────────

export default function AuthPage() {
  const navigate = useNavigate()
  const role = sessionStorage.getItem('role') || 'student'
  const roleLabel = { student: 'Student', faculty: 'Faculty', phd: 'PHD Scholar' }[role]

  const [step, setStep]     = useState('signin')
  const [error, setError]   = useState('')
  const [info, setInfo]     = useState('')
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)

  // field state
  const [email, setEmail]       = useState('')
  const [phone, setPhone]       = useState('')
  const [otp, setOtp]           = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [fullName, setFullName] = useState('')
  const [remember, setRemember] = useState(false)

  const go = (s) => { setStep(s); setError(''); setInfo(''); setOtp('') }

  const wrap = async (fn) => {
    setError(''); setInfo(''); setLoading(true)
    try { await fn() } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  // ── Sign In ──────────────────────────────────────────────────
  const handleSignIn = (e) => { e.preventDefault(); wrap(async () => {
    const data = await api.post('/auth/login', { email_or_phone: email, password })
    localStorage.setItem('token', data.token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    navigate('/dashboard')
  })}

  // ── Sign Up step 1: initiate ─────────────────────────────────
  const handleSignupInit = (e) => { e.preventDefault(); wrap(async () => {
    await api.post('/auth/signup/initiate/email', { email })
    setInfo(`OTP sent to ${email}`)
    go('signup_otp')
  })}

  // ── Sign Up step 2: verify OTP ───────────────────────────────
  const handleSignupOtp = (e) => { e.preventDefault(); wrap(async () => {
    await api.post('/auth/signup/verify', { email_or_phone: email, otp })
    go('signup_pass')
  })}

  // ── Sign Up step 3: set password ─────────────────────────────
  const handleSignupPass = (e) => { e.preventDefault(); wrap(async () => {
    if (password !== confirm) throw new Error('Passwords do not match')
    await api.post('/auth/signup/set-password', { email_or_phone: email, password })
    setInfo('Account created! Please sign in.')
    go('signin')
  })}

  // ── Forgot step 1: initiate ──────────────────────────────────
  const handleForgotInit = (e) => { e.preventDefault(); wrap(async () => {
    await api.post('/auth/forgot-password/initiate', { email_or_phone: email })
    setInfo(`OTP sent to ${email}`)
    go('forgot_otp')
  })}

  // ── Forgot step 2: verify OTP ────────────────────────────────
  const handleForgotOtp = (e) => { e.preventDefault(); wrap(async () => {
    await api.post('/auth/forgot-password/verify', { email_or_phone: email, otp })
    go('forgot_pass')
  })}

  // ── Forgot step 3: reset password ───────────────────────────
  const handleForgotPass = (e) => { e.preventDefault(); wrap(async () => {
    if (password !== confirm) throw new Error('Passwords do not match')
    await api.post('/auth/forgot-password/reset', { email_or_phone: email, password })
    setInfo('Password reset! Please sign in.')
    go('signin')
  })}

  // ── Resend OTP ───────────────────────────────────────────────
  const resendOtp = () => wrap(async () => {
    if (step === 'signup_otp') await api.post('/auth/signup/initiate/email', { email })
    else await api.post('/auth/forgot-password/initiate', { email_or_phone: email })
    setInfo('OTP resent!')
  })

  // ── helpers ──────────────────────────────────────────────────
  const isOtpStep   = step === 'signup_otp'  || step === 'forgot_otp'
  const isPassStep  = step === 'signup_pass' || step === 'forgot_pass'
  const isSignup    = step.startsWith('signup')
  const isForgot    = step.startsWith('forgot')

  const stepTitle = {
    signin:      'Welcome back',
    signup_init: 'Create account',
    signup_otp:  'Verify your email',
    signup_pass: 'Set your password',
    forgot_init: 'Forgot password',
    forgot_otp:  'Verify your email',
    forgot_pass: 'Reset password',
  }[step]

  const stepSub = {
    signin:      `Signing in as ${roleLabel}`,
    signup_init: `Registering as ${roleLabel}`,
    signup_otp:  `Enter the OTP sent to ${email}`,
    signup_pass: 'Choose a strong password',
    forgot_init: 'Enter your registered email',
    forgot_otp:  `Enter the OTP sent to ${email}`,
    forgot_pass: 'Enter your new password',
  }[step]

  return (
    <div className={styles.page}>
      {/* ── LEFT PANEL ── */}
      <div className={styles.left}>
        <div className={styles.leftInner}>
          <button className={styles.backBtn} onClick={() => navigate('/')}>← Back</button>
          <div className={styles.brand}>
            <div className={styles.brandIcon}>
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <rect width="28" height="28" rx="8" fill="#415E72"/>
                <rect x="6" y="7" width="16" height="14" rx="2" stroke="white" strokeWidth="1.8" fill="none"/>
                <path d="M6 11h16" stroke="white" strokeWidth="1.8"/>
                <rect x="9" y="14" width="3" height="3" rx="0.5" fill="white"/>
                <rect x="13" y="14" width="3" height="3" rx="0.5" fill="white"/>
              </svg>
            </div>
            <span className={styles.brandName}>TimeTable<span className={styles.brandAccent}>OCR</span></span>
          </div>
          <div className={styles.rolePill}>{roleLabel}</div>
          <h1 className={styles.headline}>
            Extract timetables<br />from images —<br />
            <span className={styles.headlineAccent}>get smart reminders</span>
          </h1>
          <p className={styles.subtext}>
            Upload a photo of your timetable. Our AI parses it into structured data,
            stores it in Supabase, and automates class reminders.
          </p>
          <div className={styles.features}>
            {[
              { icon: '📷', title: 'AI Timetable OCR',    desc: 'Extract structured time, day & subject data automatically' },
              { icon: '⚡', title: 'Instant JSON Export',  desc: 'Clean REST API output ready for any app integration' },
              { icon: '🔔', title: 'Smart Reminders',      desc: 'APScheduler triggers alerts based on your class times' },
            ].map(f => (
              <div key={f.title} className={styles.feature}>
                <span className={styles.featureIcon}>{f.icon}</span>
                <div>
                  <div className={styles.featureTitle}>{f.title}</div>
                  <div className={styles.featureDesc}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
          <div className={styles.stats}>
            <div className={styles.stat}><span className={styles.statNum}>99%</span><span className={styles.statLabel}>OCR Accuracy</span></div>
            <div className={styles.statDivider}/>
            <div className={styles.stat}><span className={styles.statNum}>5s</span><span className={styles.statLabel}>Parse Time</span></div>
            <div className={styles.statDivider}/>
            <div className={styles.stat}><span className={styles.statNum}>∞</span><span className={styles.statLabel}>Reminders</span></div>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL ── */}
      <div className={styles.right}>
        <div className={styles.formWrap}>
          <div className={styles.formTop}>
            <div className={styles.avatarCircle}>
              {role === 'student' ? '🎓' : role === 'faculty' ? '💼' : '🔬'}
            </div>
            <div>
              <h2 className={styles.welcomeTitle}>{stepTitle}</h2>
              <p className={styles.welcomeSub}>{stepSub}</p>
            </div>
          </div>

          {/* Tab bar — only on signin / signup_init */}
          {(step === 'signin' || step === 'signup_init') && (
            <div className={styles.tabs}>
              <button className={`${styles.tab} ${step === 'signin' ? styles.activeTab : ''}`}
                onClick={() => go('signin')}>Sign In</button>
              <button className={`${styles.tab} ${step === 'signup_init' ? styles.activeTab : ''}`}
                onClick={() => go('signup_init')}>Sign Up</button>
            </div>
          )}

          {/* Step breadcrumb for multi-step */}
          {(isOtpStep || isPassStep) && (
            <div className={styles.stepBar}>
              <span className={styles.stepDone}>✓ Email</span>
              <span className={styles.stepArrow}>›</span>
              <span className={isPassStep ? styles.stepDone : styles.stepActive}>
                {isPassStep ? '✓ OTP' : 'OTP'}
              </span>
              <span className={styles.stepArrow}>›</span>
              <span className={isPassStep ? styles.stepActive : styles.stepPending}>Password</span>
            </div>
          )}

          {error && <div className={styles.errorBox}><span>⚠️</span> {error}</div>}
          {info  && <div className={styles.infoBox}><span>ℹ️</span> {info}</div>}

          {/* ── SIGN IN ── */}
          {step === 'signin' && (
            <form onSubmit={handleSignIn} className={styles.form}>
              <div className={styles.field}>
                <label>Email or Phone</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>✉️</span>
                  <input type="text" placeholder="student@university.edu"
                    value={email} onChange={e => setEmail(e.target.value)} required />
                </div>
              </div>
              <div className={styles.field}>
                <div className={styles.labelRow}>
                  <label>Password</label>
                  <button type="button" className={styles.forgotBtn}
                    onClick={() => go('forgot_init')}>Forgot password?</button>
                </div>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🔒</span>
                  <input type={showPass ? 'text' : 'password'} placeholder="Enter your password"
                    value={password} onChange={e => setPassword(e.target.value)} required />
                  <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(p => !p)}>
                    {showPass ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>
              <label className={styles.checkLabel}>
                <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
                <span>Remember me for 30 days</span>
              </label>
              <button type="submit" className={styles.primaryBtn} disabled={loading}>
                {loading ? <span className={styles.spinner}/> : null}
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
              <div className={styles.dividerRow}><span>or continue with</span></div>
              <div className={styles.socialRow}>
                <button type="button" className={styles.socialBtn}>
                  <svg width="18" height="18" viewBox="0 0 18 18"><path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/><path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/><path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/><path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/></svg>
                  Google
                </button>
                <button type="button" className={styles.socialBtn}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
                  GitHub
                </button>
              </div>
              <p className={styles.switchText}>
                Don't have an account?{' '}
                <button type="button" className={styles.switchBtn} onClick={() => go('signup_init')}>Create one</button>
              </p>
            </form>
          )}

          {/* ── SIGNUP STEP 1: email ── */}
          {step === 'signup_init' && (
            <form onSubmit={handleSignupInit} className={styles.form}>
              <div className={styles.field}>
                <label>Full Name</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>👤</span>
                  <input type="text" placeholder="John Doe" value={fullName}
                    onChange={e => setFullName(e.target.value)} required />
                </div>
              </div>
              <div className={styles.field}>
                <label>Email</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>✉️</span>
                  <input type="email" placeholder="you@university.edu" value={email}
                    onChange={e => setEmail(e.target.value)} required />
                </div>
              </div>
              <button type="submit" className={styles.primaryBtn} disabled={loading}>
                {loading ? <span className={styles.spinner}/> : null}
                {loading ? 'Sending OTP…' : 'Send OTP'}
              </button>
              <p className={styles.switchText}>
                Already have an account?{' '}
                <button type="button" className={styles.switchBtn} onClick={() => go('signin')}>Sign in</button>
              </p>
            </form>
          )}

          {/* ── OTP VERIFY (signup + forgot) ── */}
          {isOtpStep && (
            <form onSubmit={isSignup ? handleSignupOtp : handleForgotOtp} className={styles.form}>
              <div className={styles.field}>
                <label>One-Time Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🔑</span>
                  <input type="text" placeholder="Enter 6-digit OTP" maxLength={6}
                    value={otp} onChange={e => setOtp(e.target.value)} required
                    className={styles.otpInput} />
                </div>
              </div>
              <button type="submit" className={styles.primaryBtn} disabled={loading}>
                {loading ? <span className={styles.spinner}/> : null}
                {loading ? 'Verifying…' : 'Verify OTP'}
              </button>
              <p className={styles.switchText}>
                Didn't receive it?{' '}
                <button type="button" className={styles.switchBtn} onClick={resendOtp}>Resend OTP</button>
              </p>
              <p className={styles.switchText}>
                <button type="button" className={styles.switchBtn}
                  onClick={() => go(isSignup ? 'signup_init' : 'forgot_init')}>← Change email</button>
              </p>
            </form>
          )}

          {/* ── SET / RESET PASSWORD ── */}
          {isPassStep && (
            <form onSubmit={isSignup ? handleSignupPass : handleForgotPass} className={styles.form}>
              <div className={styles.field}>
                <label>New Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🔒</span>
                  <input type={showPass ? 'text' : 'password'} placeholder="Min 8 characters"
                    value={password} onChange={e => setPassword(e.target.value)} required />
                  <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(p => !p)}>
                    {showPass ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>
              <div className={styles.field}>
                <label>Confirm Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🔒</span>
                  <input type={showPass ? 'text' : 'password'} placeholder="Repeat password"
                    value={confirm} onChange={e => setConfirm(e.target.value)} required />
                </div>
              </div>
              <button type="submit" className={styles.primaryBtn} disabled={loading}>
                {loading ? <span className={styles.spinner}/> : null}
                {loading ? 'Saving…' : isSignup ? 'Create Account' : 'Reset Password'}
              </button>
            </form>
          )}

          {/* ── FORGOT INIT ── */}
          {step === 'forgot_init' && (
            <form onSubmit={handleForgotInit} className={styles.form}>
              <div className={styles.field}>
                <label>Email or Phone</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>✉️</span>
                  <input type="text" placeholder="student@university.edu"
                    value={email} onChange={e => setEmail(e.target.value)} required />
                </div>
              </div>
              <button type="submit" className={styles.primaryBtn} disabled={loading}>
                {loading ? <span className={styles.spinner}/> : null}
                {loading ? 'Sending OTP…' : 'Send Reset OTP'}
              </button>
              <p className={styles.switchText}>
                <button type="button" className={styles.switchBtn} onClick={() => go('signin')}>← Back to Sign In</button>
              </p>
            </form>
          )}
        </div>

        <footer className={styles.footer}>
          <span>About</span><span>Docs</span><span>Support</span>
          <span className={styles.footerRight}>© 2026 TimetableOCR — FastAPI &amp; Supabase</span>
        </footer>
      </div>
    </div>
  )
}
