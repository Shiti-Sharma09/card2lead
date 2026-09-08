export default function AssignSelect({ options, value, onChange }) {
  return (
    <div>
      <label className="field-label">Assign</label>
      <select
        className={`field-input ${value ? '' : 'text-slate-400'}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select assignee</option>
        {options.map((name) => (
          <option key={name} value={name} className="text-ink">
            {name}
          </option>
        ))}
      </select>
    </div>
  )
}
