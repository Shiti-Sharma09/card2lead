export default function Logo({ className = '' }) {
  return (
    <div className={`flex items-center gap-2 font-extrabold tracking-tight ${className}`}>
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-lg text-white">
        C
      </span>
      <span>
        CARD<span className="text-brand">2</span>LEAD
      </span>
    </div>
  )
}
