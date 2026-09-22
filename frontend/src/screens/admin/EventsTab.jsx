import { useState } from 'react'
import { createEvent, updateEvent } from '../../lib/api'

const emptyForm = {
  name: '',
  description: '',
  location: '',
  organizer: '',
  start_date: '',
  end_date: '',
}

function toCreatePayload(form) {
  const payload = { name: form.name.trim() }
  if (form.description.trim()) payload.description = form.description.trim()
  if (form.location.trim()) payload.location = form.location.trim()
  if (form.organizer.trim()) payload.organizer = form.organizer.trim()
  if (form.start_date) payload.start_date = form.start_date
  if (form.end_date) payload.end_date = form.end_date
  return payload
}

function toUpdatePayload(form) {
  return {
    description: form.description.trim(),
    location: form.location.trim(),
    organizer: form.organizer.trim(),
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    is_active: form.is_active,
  }
}

export default function EventsTab({ events, loading, onToast, onChanged }) {
  const [form, setForm] = useState(emptyForm)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [saving, setSaving] = useState(false)

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submitCreate = async (e) => {
    e.preventDefault()
    const name = form.name.trim()
    if (!name) return
    setCreating(true)
    try {
      await createEvent(toCreatePayload(form))
      setForm(emptyForm)
      onToast?.(`"${name}" created — a Sheet tab was added for it.`)
      await onChanged?.()
    } catch (err) {
      onToast?.(err.message || 'Could not create the event.')
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (ev) => {
    setEditingId(ev.id)
    setEditForm({
      description: ev.description || '',
      location: ev.location || '',
      organizer: ev.organizer || '',
      start_date: ev.start_date || '',
      end_date: ev.end_date || '',
      is_active: ev.is_active,
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm(null)
  }

  const submitEdit = async (id) => {
    setSaving(true)
    try {
      await updateEvent(id, toUpdatePayload(editForm))
      onToast?.('Event updated.')
      cancelEdit()
      await onChanged?.()
    } catch (err) {
      onToast?.(err.message || 'Could not update the event.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submitCreate} className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold">Create event</h2>
        <p className="mt-1 text-xs text-slate-500">
          Creates a new tab in the Google Sheet named after the event.
        </p>

        <div className="mt-3 space-y-3">
          <div>
            <label className="field-label">Name *</label>
            <input className="field-input" value={form.name} onChange={update('name')} required />
          </div>
          <div>
            <label className="field-label">Description</label>
            <input className="field-input" value={form.description} onChange={update('description')} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="field-label">Location</label>
              <input className="field-input" value={form.location} onChange={update('location')} />
            </div>
            <div>
              <label className="field-label">Organizer</label>
              <input className="field-input" value={form.organizer} onChange={update('organizer')} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="field-label">Start date</label>
              <input
                type="date"
                className="field-input"
                value={form.start_date}
                onChange={update('start_date')}
              />
            </div>
            <div>
              <label className="field-label">End date</label>
              <input
                type="date"
                className="field-input"
                value={form.end_date}
                onChange={update('end_date')}
              />
            </div>
          </div>
        </div>

        <button className="btn-primary mt-4 w-full" disabled={creating || !form.name.trim()}>
          {creating ? 'Creating…' : 'Create event'}
        </button>
      </form>

      <div>
        <h2 className="font-semibold">Existing events</h2>
        {loading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
        {!loading && events.length === 0 && (
          <p className="mt-2 text-sm text-slate-500">No events yet — create one above.</p>
        )}

        <div className="mt-2 space-y-2">
          {events.map((ev) => (
            <div key={ev.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{ev.name}</span>
                    {!ev.is_active && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                        inactive
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {[ev.location, ev.organizer].filter(Boolean).join(' · ') || '—'}
                    {ev.start_date && (
                      <>
                        {' '}
                        · {ev.start_date}
                        {ev.end_date ? ` – ${ev.end_date}` : ''}
                      </>
                    )}
                  </div>
                  {ev.google_tab_name && (
                    <div className="mt-0.5 text-xs text-slate-400">
                      Sheet tab: {ev.google_tab_name}
                    </div>
                  )}
                </div>
                <button
                  className="shrink-0 text-sm font-medium text-brand"
                  onClick={() => (editingId === ev.id ? cancelEdit() : startEdit(ev))}
                >
                  {editingId === ev.id ? 'Cancel' : 'Edit'}
                </button>
              </div>

              {editingId === ev.id && editForm && (
                <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                  <div>
                    <label className="field-label">Description</label>
                    <input
                      className="field-input"
                      value={editForm.description}
                      onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="field-label">Location</label>
                      <input
                        className="field-input"
                        value={editForm.location}
                        onChange={(e) => setEditForm((f) => ({ ...f, location: e.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="field-label">Organizer</label>
                      <input
                        className="field-input"
                        value={editForm.organizer}
                        onChange={(e) => setEditForm((f) => ({ ...f, organizer: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="field-label">Start date</label>
                      <input
                        type="date"
                        className="field-input"
                        value={editForm.start_date}
                        onChange={(e) => setEditForm((f) => ({ ...f, start_date: e.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="field-label">End date</label>
                      <input
                        type="date"
                        className="field-input"
                        value={editForm.end_date}
                        onChange={(e) => setEditForm((f) => ({ ...f, end_date: e.target.value }))}
                      />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={editForm.is_active}
                      onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                    />
                    Active (assigned users can use it to scan)
                  </label>
                  <button
                    className="btn-primary w-full"
                    disabled={saving}
                    onClick={() => submitEdit(ev.id)}
                  >
                    {saving ? 'Saving…' : 'Save changes'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
