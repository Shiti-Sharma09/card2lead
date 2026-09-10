export default function Field({
  label,
  value,
  onChange,
  hint,
  hintTone = 'amber',
  type = 'text',
  inputMode,
  placeholder,
}) {
  const hintColor = hintTone === 'error' ? 'text-rose-600' : 'text-amber-600'
  return (
    <div>
      <label className="field-label">{label}</label>
      <input
        className="field-input"
        value={value}
        type={type}
        inputMode={inputMode}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && <p className={`mt-1 text-xs ${hintColor}`}>{hint}</p>}
    </div>
  )
}
