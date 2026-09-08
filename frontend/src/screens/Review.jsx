import { useMemo, useState } from 'react'
import Field from '../components/Field'
import AssignSelect from '../components/AssignSelect'
import Logo from '../components/Logo'

const FIELD_DEFS = [
  { key: 'name', label: 'Name', placeholder: 'Full name' },
  { key: 'company', label: 'Company', placeholder: 'Organisation' },
  { key: 'title', label: 'Title', placeholder: 'Job title / designation' },
  {
    key: 'email',
    label: 'Email',
    placeholder: 'name@company.com',
    type: 'email',
    inputMode: 'email',
  },
  {
    key: 'phone',
    label: 'Phone Number',
    placeholder: '+91 XXXXX XXXXX',
    inputMode: 'tel',
  },
]

const emailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.split(',')[0].trim())

export default function Review({
  imageUrl,
  extraction,
  assignees,
  saving,
  onSave,
  onRestart,
}) {
  const [form, setForm] = useState({
    name: extraction.fields?.name || '',
    company: extraction.fields?.company || '',
    title: extraction.fields?.title || '',
    email: extraction.fields?.email || '',
    phone: extraction.fields?.phone || '',
    notes: '',
    assignedTo: '',
  })

  const update = (key) => (value) => setForm((f) => ({ ...f, [key]: value }))

  const errors = useMemo(() => {
    const e = {}
    if (!form.name.trim()) e.name = 'empty'
    if (!form.assignedTo) e.assignedTo = 'empty'
    if (form.email.trim() && !emailOk(form.email)) e.email = 'format'
    return e
  }, [form])

  const canSave = Object.keys(errors).length === 0 && !saving

  return (
    <div className="mx-auto max-w-md px-5 pb-28 pt-6">
      <Logo className="text-lg" />

      {extraction.mock && (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Demo mode: these values are sample data (no Groq key set), not read from
          your card.
        </p>
      )}

      <h2 className="mt-5 text-lg font-bold">Review the details</h2>
      <p className="text-sm text-slate-500">
        Every field is editable. Name and Assigned To are required.
      </p>

      {imageUrl && (
        <img
          src={imageUrl}
          alt="Captured card"
          className="mt-4 w-full rounded-xl border border-slate-200 object-contain"
        />
      )}

      <div className="mt-5 space-y-4">
        {FIELD_DEFS.map((d) => (
          <Field
            key={d.key}
            label={d.label}
            placeholder={d.placeholder}
            type={d.type}
            inputMode={d.inputMode}
            value={form[d.key]}
            onChange={update(d.key)}
            hint={
              d.key === 'email' && errors.email === 'format'
                ? 'That doesn’t look like an email address'
                : undefined
            }
            hintTone="error"
          />
        ))}

        <div>
          <label className="field-label">Notes</label>
          <textarea
            className="field-input min-h-[96px] resize-y"
            placeholder="Where you met, what they need, follow-up&hellip;"
            value={form.notes}
            onChange={(e) => update('notes')(e.target.value)}
          />
        </div>

        <AssignSelect
          options={assignees}
          value={form.assignedTo}
          onChange={update('assignedTo')}
        />
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-slate-200 bg-white/95 px-5 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-md gap-3">
          <button className="btn-ghost flex-1" onClick={onRestart} disabled={saving}>
            Discard
          </button>
          <button
            className="btn-primary flex-[2]"
            onClick={() => onSave(form)}
            disabled={!canSave}
          >
            {saving ? 'Saving…' : 'SAVE'}
          </button>
        </div>
      </div>
    </div>
  )
}
