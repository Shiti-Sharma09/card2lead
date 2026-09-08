export default function AssignSelect({ options, value, onChange }) {
  return (
    <div>
      <label className="field-label">Assigned To</label>
      <select
        className={`field-input ${value ? '' : 'text-slate-400'}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select a name</option>
        {options.map((name) => (
          <option key={name} value={name} className="text-ink">
            {name}
          </option>
        ))}
      </select>
    </div>
  )
}
