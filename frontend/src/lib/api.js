import { API_BASE } from './config'
import { getToken, setToken } from './auth'

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function messageFrom(data, status) {
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) {
    return data.detail[0]?.msg || 'Please check the form and try again.'
  }
  if (typeof data?.message === 'string') return data.message
  return `Request failed (${status}).`
}

async function request(path, { method = 'GET', json, form, auth = true } = {}) {
  const headers = {}
  const token = getToken()
  if (auth && token) headers.Authorization = `Bearer ${token}`

  let body
  if (form) {
    body = form
  } else if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  }

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, { method, headers, body })
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.')
  }

  if (res.status === 401) {
    setToken(null)
    throw new ApiError(401, 'Your session has expired. Please log in again.')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, messageFrom(data, res.status))
  return data
}

export const login = (email, password) =>
  request('/auth/login', { method: 'POST', json: { email, password }, auth: false })

export const register = (email, password) =>
  request('/auth/register', { method: 'POST', json: { email, password }, auth: false })

export const fetchMe = () => request('/auth/me')
export const fetchMyEvents = () => request('/me/events')
export const fetchAssignees = () => request('/assignees')

export function scanCard(eventId, blob) {
  const form = new FormData()
  form.append('image', blob, 'card.jpg')
  return request(`/events/${eventId}/scan`, { method: 'POST', form })
}

export function saveLead(eventId, payload) {
  return request(`/events/${eventId}/leads`, { method: 'POST', json: payload })
}

export { getToken, setToken }
