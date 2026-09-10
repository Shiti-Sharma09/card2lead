import Logo from '../components/Logo'

export default function Success({ assignee, duplicate, eventName, onAgain, onChangeEvent }) {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col items-center px-5 pb-10 pt-16 text-center">
      <Logo className="text-lg" />

      <div className="mt-16 grid h-20 w-20 place-items-center rounded-full bg-emerald-100 text-4xl text-emerald-600">
        &#10003;
      </div>

      <h2 className="mt-6 text-xl font-bold">
        {duplicate ? 'Already saved' : 'Lead saved'}
      </h2>
      <p className="mt-2 text-slate-500">
        {duplicate ? (
          'This card was already recorded — no duplicate row was added.'
        ) : (
          <>
            Saved to <span className="font-semibold text-ink">{eventName}</span>,
            assigned to <span className="font-semibold text-ink">{assignee}</span>.
          </>
        )}
      </p>

      <button className="btn-primary mt-10 w-full" onClick={onAgain}>
        Capture another lead
      </button>
      <button className="mt-3 text-sm text-slate-500" onClick={onChangeEvent}>
        Switch event
      </button>
    </div>
  )
}
