export default function Field({
  label,
  value,
  onChange,
  flag = false,
  hint,
  hintTone = 'amber',
  type = 'text',
  inputMode,
  placeholder,
}) {
  const hintColor = hintTone === 'error' ? 'text-rose-600' : 'text-amber-600'
  return (
    <div>
      <label className="field-label">
        {label}
        {flag && (
          <span className="ml-2 text-xs font-semibold text-amber-600">please verify</span>
        )}
      </label>
      <input
        className={`field-input ${flag ? 'field-input--flag' : ''}`}
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
