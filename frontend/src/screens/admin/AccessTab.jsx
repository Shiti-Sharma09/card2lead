import { useCallback, useEffect, useState } from 'react'
import { fetchEventAccess, grantEventAccess, revokeEventAccess } from '../../lib/api'

export default function AccessTab({ events, loading, onToast }) {
  const [eventId, setEventId] = useState('')
  const [rows, setRows] = useState([])
  const [rowsLoading, setRowsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [granting, setGranting] = useState(false)

  useEffect(() => {
    if (!eventId && events.length > 0) setEventId(String(events[0].id))
  }, [events, eventId])

  const load = useCallback(async () => {
    if (!eventId) return
    setRowsLoading(true)
    try {
      setRows(await fetchEventAccess(eventId))
    } catch (e) {
      onToast?.(e.message)
    } finally {
      setRowsLoading(false)
    }
  }, [eventId, onToast])

  useEffect(() => {
    load()
  }, [load])

  const submitGrant = async (e) => {
    e.preventDefault()
    const value = email.trim()
    if (!value) return
    setGranting(true)
    try {
      await grantEventAccess(eventId, value)
      setEmail('')
      onToast?.(`Access granted to ${value}.`)
      await load()
    } catch (err) {
      onToast?.(err.message || 'Could not grant access.')
    } finally {
      setGranting(false)
    }
  }

  const revoke = async (userId, userEmail) => {
    try {
      await revokeEventAccess(eventId, userId)
      onToast?.(`Access revoked for ${userEmail}.`)
      await load()
    } catch (err) {
      onToast?.(err.message || 'Could not revoke access.')
    }
  }

  if (!loading && events.length === 0) {
    return <p className="text-sm text-slate-500">Create an event first, on the Events tab.</p>
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="field-label">Event</label>
        <select
          className="field-input"
          value={eventId}
          onChange={(e) => setEventId(e.target.value)}
        >
          {events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.name}
            </option>
          ))}
        </select>
      </div>

      <form onSubmit={submitGrant} className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold">Grant access</h2>
        <p className="mt-1 text-xs text-slate-500">
          The person must already have a card2lead account — they can self-register
          on the login screen.
        </p>
        <div className="mt-3 flex gap-2">
          <input
            className="field-input"
            type="email"
            placeholder="name@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button className="btn-primary shrink-0" disabled={granting || !email.trim()}>
            {granting ? 'Adding…' : 'Grant'}
          </button>
        </div>
      </form>

      <div>
        <h2 className="font-semibold">Who has access</h2>
        {rowsLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
        {!rowsLoading && rows.length === 0 && (
          <p className="mt-2 text-sm text-slate-500">No one has been granted access yet.</p>
        )}
        <div className="mt-2 space-y-2">
          {rows.map((r) => (
            <div
              key={r.user_id}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
            >
              <span className="text-sm">{r.email}</span>
              <button
                className="text-sm font-medium text-rose-600"
                onClick={() => revoke(r.user_id, r.email)}
              >
                Revoke
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
