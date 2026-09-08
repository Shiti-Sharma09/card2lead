import { useCallback, useEffect, useRef, useState } from 'react'
import Landing from './screens/Landing'
import Camera from './screens/Camera'
import Review from './screens/Review'
import Success from './screens/Success'
import Blurry from './screens/Blurry'
import Spinner from './components/Spinner'
import Toast from './components/Toast'
import { extractCard, fetchConfig, saveLead } from './lib/api'
import { downscaleToJpeg } from './lib/image'
import { CONFIDENCE_THRESHOLD, FALLBACK_ASSIGNEES } from './lib/config'

// screen: landing | camera | processing | review | blurry | success
export default function App() {
  const [screen, setScreen] = useState('landing')
  const [cfg, setCfg] = useState({
    assignees: FALLBACK_ASSIGNEES,
    confidenceThreshold: CONFIDENCE_THRESHOLD,
    mockMode: false,
  })
  const [extraction, setExtraction] = useState(null)
  const [imageUrl, setImageUrl] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(null)
  const [toast, setToast] = useState('')
  const imageUrlRef = useRef(null)

  useEffect(() => {
    fetchConfig().then((c) => {
      if (!c) return
      setCfg((prev) => ({
        ...prev,
        ...c,
        assignees: c.assignees?.length ? c.assignees : prev.assignees,
      }))
    })
  }, [])

  const setImage = useCallback((blob) => {
    if (imageUrlRef.current) URL.revokeObjectURL(imageUrlRef.current)
    const url = blob ? URL.createObjectURL(blob) : null
    imageUrlRef.current = url
    setImageUrl(url)
  }, [])

  const runExtraction = useCallback(
    async (blob) => {
      if (!blob || blob.size === 0) {
        setToast('That image didn’t capture properly. Please try again.')
        setScreen('landing')
        return
      }
      setScreen('processing')
      const prepared = await downscaleToJpeg(blob)
      setImage(prepared)
      try {
        const data = await extractCard(prepared)
        if (data.blurry) {
          setScreen('blurry')
          return
        }
        setExtraction(data)
        setScreen('review')
      } catch (e) {
        setToast(e.message || 'Something went wrong. Please try again.')
        setScreen('landing')
      }
    },
    [setImage],
  )

  const handleSave = useCallback(async (form) => {
    setSaving(true)
    try {
      const { status, data } = await saveLead(form)
      if (status === 200 && data.ok) {
        setSaved({ assignee: form.assignedTo, row: data.row })
        setScreen('success')
      } else if (status === 409) {
        setToast(data.message || 'The Excel file is open. Close it and press Save again.')
      } else if (status === 422) {
        setToast('Please complete every field correctly before saving.')
      } else {
        setToast(data.message || 'Could not save the lead. Please try again.')
      }
    } catch {
      setToast('Network error while saving. Check your connection and retry.')
    } finally {
      setSaving(false)
    }
  }, [])

  const reset = useCallback(() => {
    setExtraction(null)
    setSaved(null)
    setImage(null)
    setScreen('landing')
  }, [setImage])

  return (
    <div className="min-h-full">
      {screen === 'landing' && (
        <Landing
          mockMode={cfg.mockMode}
          onCamera={() => setScreen('camera')}
          onUpload={runExtraction}
        />
      )}

      {screen === 'camera' && (
        <Camera onCaptured={runExtraction} onCancel={() => setScreen('landing')} />
      )}

      {screen === 'processing' && (
        <div className="grid min-h-screen place-items-center">
          <Spinner label="Reading the card&hellip;" />
        </div>
      )}

      {screen === 'blurry' && (
        <div className="min-h-screen">
          <Blurry onRetake={() => setScreen('camera')} onUpload={runExtraction} />
        </div>
      )}

      {screen === 'review' && extraction && (
        <Review
          imageUrl={imageUrl}
          extraction={extraction}
          assignees={cfg.assignees}
          threshold={cfg.confidenceThreshold}
          saving={saving}
          onSave={handleSave}
          onRestart={reset}
        />
      )}

      {screen === 'success' && saved && (
        <Success assignee={saved.assignee} row={saved.row} onAgain={reset} />
      )}

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
