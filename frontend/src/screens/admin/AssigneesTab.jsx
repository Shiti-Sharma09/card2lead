import { useCallback, useEffect, useState } from 'react'
import { addAssignee, fetchAllAssignees, removeAssignee } from '../../lib/api'

export default function AssigneesTab({ onToast }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await fetchAllAssignees())
    } catch (e) {
      onToast?.(e.message)
    } finally {
      setLoading(false)
    }
  }, [onToast])

  useEffect(() => {
    load()
  }, [load])

  const submitAdd = async (e) => {
    e.preventDefault()
    const value = name.trim()
    if (!value) return
    setBusy(true)
    try {
      await addAssignee(value)
      setName('')
      await load()
    } catch (err) {
      onToast?.(err.message || 'Could not add that name.')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    setBusy(true)
    try {
      await removeAssignee(id)
      await load()
    } catch (err) {
      onToast?.(err.message || 'Could not remove that name.')
    } finally {
      setBusy(false)
    }
  }

  const readd = async (existingName) => {
    setBusy(true)
    try {
      await addAssignee(existingName)
      await load()
    } catch (err) {
      onToast?.(err.message || 'Could not re-add that name.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submitAdd} className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold">Add a name</h2>
        <p className="mt-1 text-xs text-slate-500">
          Shown in the Assigned To dropdown on the review screen, for every event.
        </p>
        <div className="mt-3 flex gap-2">
          <input
            className="field-input"
            placeholder="e.g. PRIYA"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="btn-primary shrink-0" disabled={busy || !name.trim()}>
            Add
          </button>
        </div>
      </form>

      <div>
        <h2 className="font-semibold">Current list</h2>
        {loading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
        {!loading && rows.length === 0 && (
          <p className="mt-2 text-sm text-slate-500">No names yet — add one above.</p>
        )}
        <div className="mt-2 space-y-2">
          {rows.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
            >
              <span className={`text-sm ${a.is_active ? '' : 'text-slate-400 line-through'}`}>
                {a.name}
              </span>
              {a.is_active ? (
                <button
                  className="text-sm font-medium text-rose-600"
                  disabled={busy}
                  onClick={() => remove(a.id)}
                >
                  Remove
                </button>
              ) : (
                <button
                  className="text-sm font-medium text-brand"
                  disabled={busy}
                  onClick={() => readd(a.name)}
                >
                  Re-add
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
