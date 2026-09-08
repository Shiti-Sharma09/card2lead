import { API_BASE } from './config'

export async function fetchConfig() {
  try {
    const res = await fetch(`${API_BASE}/config`)
    if (!res.ok) throw new Error('bad status')
    return await res.json()
  } catch {
    return null
  }
}

export async function extractCard(blob) {
  const form = new FormData()
  form.append('image', blob, 'card.jpg')

  const res = await fetch(`${API_BASE}/extract`, { method: 'POST', body: form })
  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new Error(data.detail || 'Could not read the card. Please try again.')
  }
  return data
}

export async function saveLead(lead) {
  const res = await fetch(`${API_BASE}/leads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(lead),
  })
  const data = await res.json().catch(() => ({}))
  return { status: res.status, data }
}
