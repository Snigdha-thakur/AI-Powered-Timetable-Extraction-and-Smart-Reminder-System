const BASE = 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res = await fetch(BASE + path, { ...options, headers })

  // Try token refresh on 401
  if (res.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      const rRes = await fetch(BASE + '/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (rRes.ok) {
        const { token: newToken } = await rRes.json()
        localStorage.setItem('token', newToken)
        headers['Authorization'] = `Bearer ${newToken}`
        res = await fetch(BASE + path, { ...options, headers })
      } else {
        localStorage.clear()
        window.location.href = '/auth'
        return
      }
    }
  }

  const contentType = res.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await res.json() : await res.text()

  if (!res.ok) {
    const msg = data?.detail || data?.error || (typeof data === 'string' ? data : 'Request failed')
    throw new Error(msg)
  }
  return data
}

export const api = {
  delete: (path) => request(path, { method: 'DELETE' }),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  get:  (path)       => request(path, { method: 'GET' }),
  postForm: (path, formData) => {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch(BASE + path, { method: 'POST', headers, body: formData })
      .then(async res => {
        const data = await res.json()
        if (!res.ok) throw new Error(data?.detail || 'Upload failed')
        return data
      })
  }
}
