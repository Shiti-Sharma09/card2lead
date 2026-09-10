import Logo from '../components/Logo'

export default function Landing({ event, onCamera, onUpload, onChangeEvent }) {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col px-5 pb-10 pt-14">
      <div className="flex items-center justify-between">
        <Logo className="text-xl" />
        <button className="text-sm text-slate-500" onClick={onChangeEvent}>
          Change event
        </button>
      </div>

      <div className="mt-3 inline-flex w-fit rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold text-brand">
        {event.name}
      </div>

      <div className="mt-14 flex-1">
        <h1 className="text-2xl font-bold leading-snug">
          Capture a business card,
          <br />
          get a clean lead.
        </h1>
        <p className="mt-3 text-slate-500">
          Point your camera at the card. We read the details, you review and correct
          them, then it&rsquo;s saved under{' '}
          <span className="font-medium text-ink">{event.name}</span>.
        </p>
      </div>

      <div className="space-y-3">
        <button className="btn-primary w-full" onClick={onCamera}>
          <CameraIcon />
          Open Camera
        </button>

        <label className="btn-ghost w-full cursor-pointer">
          Upload a photo
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
          />
        </label>
      </div>
    </div>
  )
}

function CameraIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  )
}
