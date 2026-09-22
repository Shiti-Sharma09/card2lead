import { useCallback, useEffect, useState } from 'react'
import Logo from '../../components/Logo'
import { fetchAllEvents } from '../../lib/api'
import EventsTab from './EventsTab'
import AccessTab from './AccessTab'
import AssigneesTab from './AssigneesTab'

const TABS = [
  { key: 'events', label: 'Events' },
  { key: 'access', label: 'Access' },
  { key: 'assignees', label: 'Assigned To' },
]

export default function AdminHome({ onBack, onToast, onEventsChanged }) {
  const [tab, setTab] = useState('events')
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(true)

  const reloadEvents = useCallback(async () => {
    setEventsLoading(true)
    try {
      setEvents(await fetchAllEvents())
    } catch (e) {
      onToast?.(e.message)
    } finally {
      setEventsLoading(false)
    }
  }, [onToast])

  useEffect(() => {
    reloadEvents()
  }, [reloadEvents])

  // Events changed here (created/edited) -> also refresh the picker's list
  // (GET /me/events) so a newly created event shows up without a manual retry.
  const handleEventsChanged = useCallback(async () => {
    await reloadEvents()
    await onEventsChanged?.()
  }, [reloadEvents, onEventsChanged])

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col px-5 pb-16 pt-8">
      <div className="flex items-center justify-between">
        <Logo className="text-lg" />
        <button className="text-sm text-slate-500" onClick={onBack}>
          &larr; Back to app
        </button>
      </div>

      <h1 className="mt-8 text-2xl font-bold">Admin</h1>
      <p className="mt-1 text-sm text-slate-500">
        Manage events, who can access them, and the Assigned To list.
      </p>

      <div className="mt-6 flex gap-1 rounded-xl bg-slate-100 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition ${
              tab === t.key ? 'bg-white text-ink shadow-sm' : 'text-slate-500'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'events' && (
          <EventsTab
            events={events}
            loading={eventsLoading}
            onToast={onToast}
            onChanged={handleEventsChanged}
          />
        )}
        {tab === 'access' && (
          <AccessTab events={events} loading={eventsLoading} onToast={onToast} />
        )}
        {tab === 'assignees' && <AssigneesTab onToast={onToast} />}
      </div>
    </div>
  )
}
