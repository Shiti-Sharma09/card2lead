import { useEffect } from 'react'

const TONES = {
  error: 'bg-rose-600',
  info: 'bg-slate-800',
  success: 'bg-emerald-600',
}

export default function Toast({ message, tone = 'error', onClose }) {
  useEffect(() => {
    if (!message) return undefined
    const timer = setTimeout(onClose, 5000)
    return () => clearTimeout(timer)
  }, [message, onClose])

  if (!message) return null

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <div
        className={`${TONES[tone]} max-w-sm rounded-xl px-4 py-3 text-sm text-white shadow-lg`}
        role="alert"
      >
        {message}
      </div>
    </div>
  )
}
