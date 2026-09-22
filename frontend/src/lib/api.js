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

// --- admin -------------------------------------------------------------
// GET /events returns every event to an admin (assigned-only for a normal
// user), so it doubles as the admin's "all events" list.
export const fetchAllEvents = () => request('/events')
export const createEvent = (payload) =>
  request('/events', { method: 'POST', json: payload })
export const updateEvent = (eventId, payload) =>
  request(`/events/${eventId}`, { method: 'PATCH', json: payload })

export const fetchEventAccess = (eventId) => request(`/events/${eventId}/access`)
export const grantEventAccess = (eventId, email) =>
  request(`/events/${eventId}/access`, { method: 'POST', json: { email } })
export const revokeEventAccess = (eventId, userId) =>
  request(`/events/${eventId}/access/${userId}`, { method: 'DELETE' })

export const fetchAllAssignees = () => request('/assignees?all=true')
export const addAssignee = (name) =>
  request('/assignees', { method: 'POST', json: { name } })
export const removeAssignee = (id) => request(`/assignees/${id}`, { method: 'DELETE' })

export { getToken, setToken }
