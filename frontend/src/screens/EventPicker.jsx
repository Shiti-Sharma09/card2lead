import Logo from '../components/Logo'

export default function EventPicker({ events, loading, onPick, onLogout, onRetry }) {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col px-5 pb-10 pt-16">
      <div className="flex items-center justify-between">
        <Logo className="text-lg" />
        <button className="text-sm text-slate-500" onClick={onLogout}>
          Log out
        </button>
      </div>

      <h1 className="mt-12 text-2xl font-bold">Choose an event</h1>
      <p className="mt-2 text-sm text-slate-500">
        Cards you scan are saved under the event you pick.
      </p>

      <div className="mt-8 flex-1 space-y-3">
        {loading && <p className="text-sm text-slate-500">Loading your events…</p>}

        {!loading && events.length === 0 && (
          <div className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            You don&rsquo;t have access to any event yet. Ask your admin to add you,
            then{' '}
            <button className="font-semibold underline" onClick={onRetry}>
              refresh
            </button>
            .
          </div>
        )}

        {events.map((ev) => (
          <button
            key={ev.id}
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-brand"
            onClick={() => onPick(ev)}
          >
            <div className="font-semibold">{ev.name}</div>
            <div className="mt-0.5 text-xs text-slate-500">
              {[ev.location, ev.organizer].filter(Boolean).join(' · ') || 'Tap to select'}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
