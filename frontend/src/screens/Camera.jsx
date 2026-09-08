import { useCallback, useEffect, useRef, useState } from 'react'
import { sharpnessScore } from '../lib/blur'
import { BLUR_THRESHOLD } from '../lib/config'
import Spinner from '../components/Spinner'

// status: starting | live | checking | error
export default function Camera({ onCaptured, onCancel }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [status, setStatus] = useState('starting')
  const [error, setError] = useState('')
  const [blurWarning, setBlurWarning] = useState(false)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const start = useCallback(async () => {
    setStatus('starting')
    setError('')
    setBlurWarning(false)

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        'This browser can’t open the camera here — it needs an HTTPS address. Go back and use "Upload a photo".',
      )
      setStatus('error')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {})
      }
      setStatus('live')
    } catch (e) {
      setError(
        e?.name === 'NotAllowedError'
          ? 'Camera permission is blocked. Allow it in your browser settings, or go back and use "Upload a photo".'
          : 'Could not start the camera. Go back and use "Upload a photo" instead.',
      )
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    start()
    return stop
  }, [start, stop])

  const capture = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    setStatus('checking')

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)

    const score = sharpnessScore(canvas)
    if (score < BLUR_THRESHOLD) {
      setBlurWarning(true)
      setStatus('live')
      return
    }

    canvas.toBlob(
      (blob) => {
        stop()
        onCaptured(blob)
      },
      'image/jpeg',
      0.92,
    )
  }

  const leave = () => {
    stop()
    onCancel()
  }

  return (
    <div
      className="fixed left-0 top-0 z-50 w-full overflow-hidden bg-black"
      style={{ height: '100dvh' }}
    >
      {/* camera preview fills the whole screen */}
      <video
        ref={videoRef}
        playsInline
        autoPlay
        muted
        className="absolute inset-0 h-full w-full object-cover"
      />

      {/* card framing guide */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="aspect-[1.75/1] w-[82%] max-w-sm rounded-xl border-2 border-white/80" />
      </div>

      {/* top bar (floats over the preview) */}
      <div
        className="absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/70 to-transparent px-4 pb-8 text-white"
        style={{ paddingTop: 'calc(0.75rem + env(safe-area-inset-top))' }}
      >
        <button onClick={leave} className="rounded-md px-2 py-1 text-sm font-medium">
          &larr; Back
        </button>
        <span className="text-sm font-medium opacity-90">Frame the card</span>
        <span className="w-12" />
      </div>

      {/* status overlays */}
      {(status === 'starting' || status === 'checking') && (
        <div className="absolute inset-0 grid place-items-center bg-black/50">
          <Spinner
            label={status === 'starting' ? 'Starting camera…' : 'Checking sharpness…'}
          />
        </div>
      )}

      {/* blur warning */}
      {blurWarning && (
        <div className="absolute inset-x-0 bottom-44 flex justify-center px-4">
          <div className="rounded-lg bg-rose-600 px-4 py-2 text-center text-sm text-white shadow-lg">
            Too blurry — hold steady and tap again.
          </div>
        </div>
      )}

      {/* shutter bar (pinned to the bottom, above the phone's home bar) */}
      <div
        className="absolute inset-x-0 bottom-0 flex flex-col items-center gap-2 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-4 pt-12"
        style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom))' }}
      >
        {status === 'error' ? (
          <p className="max-w-xs text-center text-sm text-white/90">{error}</p>
        ) : (
          <>
            <button
              onClick={capture}
              disabled={status !== 'live'}
              aria-label="Capture photo"
              className="h-[76px] w-[76px] rounded-full bg-white shadow-xl ring-4 ring-white/40 transition active:scale-95 disabled:opacity-40"
            />
            <span className="text-xs font-medium text-white/80">
              {status === 'live' ? 'Tap to capture' : 'Starting camera…'}
            </span>
          </>
        )}
      </div>
    </div>
  )
}
