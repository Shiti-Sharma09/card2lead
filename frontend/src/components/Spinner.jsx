export default function Spinner({ label }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 text-slate-500">
      <span className="h-9 w-9 animate-spin rounded-full border-[3px] border-slate-200 border-t-brand" />
      {label && <p className="text-sm font-medium">{label}</p>}
    </div>
  )
}
