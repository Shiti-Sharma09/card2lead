import { useCallback, useEffect, useRef, useState } from 'react'
import Login from './screens/Login'
import EventPicker from './screens/EventPicker'
import Landing from './screens/Landing'
import Camera from './screens/Camera'
import Review from './screens/Review'
import Success from './screens/Success'
import Spinner from './components/Spinner'
import Toast from './components/Toast'
import {
  fetchAssignees,
  fetchMe,
  fetchMyEvents,
  saveLead,
  scanCard,
} from './lib/api'
import { getToken, setToken } from './lib/auth'
import { downscaleToJpeg } from './lib/image'

const newRequestId = () =>
  globalThis.crypto?.randomUUID?.() ??
  `req-${Date.now()}-${Math.random().toString(16).slice(2)}`

// screen: booting | login | events | landing | camera | processing | review | success
export default function App() {
  const [screen, setScreen] = useState('booting')
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [event, setEvent] = useState(null)
  const [assignees, setAssignees] = useState([])
  const [extraction, setExtraction] = useState(null)
  const [imageUrl, setImageUrl] = useState(null)
  const [requestId, setRequestId] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(null)
  const [toast, setToast] = useState('')
  const imageUrlRef = useRef(null)

  const setImage = useCallback((blob) => {
    if (imageUrlRef.current) URL.revokeObjectURL(imageUrlRef.current)
    const url = blob ? URL.createObjectURL(blob) : null
    imageUrlRef.current = url
    setImageUrl(url)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setEvent(null)
    setEvents([])
    setScreen('login')
  }, [])

  const loadEvents = useCallback(async () => {
    setEventsLoading(true)
    try {
      setEvents(await fetchMyEvents())
    } catch (e) {
      if (e.status === 401) return logout()
      setToast(e.message)
    } finally {
      setEventsLoading(false)
    }
  }, [logout])

  useEffect(() => {
    ;(async () => {
      if (!getToken()) {
        setScreen('login')
        return
      }
      try {
        await fetchMe()
        await loadEvents()
        setScreen('events')
      } catch {
        setToken(null)
        setScreen('login')
      }
    })()
  }, [loadEvents])

  const onAuthed = useCallback(async () => {
    await loadEvents()
    setScreen('events')
  }, [loadEvents])

  const pickEvent = useCallback(async (ev) => {
    setEvent(ev)
    setScreen('landing')
    try {
      const list = await fetchAssignees()
      setAssignees(list.map((a) => a.name))
    } catch (e) {
      if (e.status === 401) return logout()
      setToast(e.message)
    }
  }, [logout])

  const runExtraction = useCallback(
    async (blob) => {
      if (!event) return
      if (!blob || blob.size === 0) {
        setToast('That image didn’t capture properly. Please try again.')
        setScreen('landing')
        return
      }
      setScreen('processing')
      const prepared = await downscaleToJpeg(blob)
      setImage(prepared)
      try {
        const data = await scanCard(event.id, prepared)
        setExtraction(data)
        setRequestId(newRequestId())
        setScreen('review')
      } catch (e) {
        if (e.status === 401) return logout()
        setToast(e.message || 'Could not read the card. Please try again.')
        setScreen('landing')
      }
    },
    [event, setImage, logout],
  )

  const handleSave = useCallback(
    async (form) => {
      if (!event) return
      setSaving(true)
      try {
        const data = await saveLead(event.id, {
          name: form.name,
          company: form.company,
          title: form.title,
          email: form.email,
          phone: form.phone,
          notes: form.notes,
          assigned_to: form.assignedTo,
          request_id: requestId,
        })
        setSaved({ assignee: form.assignedTo, duplicate: !!data.duplicate })
        setScreen('success')
      } catch (e) {
        if (e.status === 401) return logout()
        setToast(e.message || 'Could not save the lead. Please try again.')
      } finally {
        setSaving(false)
      }
    },
    [event, requestId, logout],
  )

  const newCard = useCallback(() => {
    setExtraction(null)
    setSaved(null)
    setImage(null)
    setScreen('landing')
  }, [setImage])

  if (screen === 'booting') {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Loading…" />
      </div>
    )
  }

  return (
    <div className="min-h-full">
      {screen === 'login' && <Login onAuthed={onAuthed} />}

      {screen === 'events' && (
        <EventPicker
          events={events}
          loading={eventsLoading}
          onPick={pickEvent}
          onLogout={logout}
          onRetry={loadEvents}
        />
      )}

      {screen === 'landing' && event && (
        <Landing
          event={event}
          onCamera={() => setScreen('camera')}
          onUpload={runExtraction}
          onChangeEvent={() => setScreen('events')}
        />
      )}

      {screen === 'camera' && (
        <Camera onCaptured={runExtraction} onCancel={() => setScreen('landing')} />
      )}

      {screen === 'processing' && (
        <div className="grid min-h-screen place-items-center">
          <Spinner label="Reading the card…" />
        </div>
      )}

      {screen === 'review' && extraction && (
        <Review
          imageUrl={imageUrl}
          extraction={extraction}
          assignees={assignees}
          saving={saving}
          onSave={handleSave}
          onRestart={newCard}
        />
      )}

      {screen === 'success' && saved && (
        <Success
          assignee={saved.assignee}
          duplicate={saved.duplicate}
          eventName={event?.name}
          onAgain={newCard}
          onChangeEvent={() => setScreen('events')}
        />
      )}

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
