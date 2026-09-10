import { useState } from 'react'
import Logo from '../components/Logo'
import { login, register } from '../lib/api'
import { setToken } from '../lib/auth'

export default function Login({ onAuthed }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (mode === 'register' && password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setBusy(true)
    try {
      const fn = mode === 'login' ? login : register
      const { access_token } = await fn(email.trim(), password)
      setToken(access_token)
      onAuthed()
    } catch (err) {
      setError(err.message || 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col px-5 pb-10 pt-16">
      <Logo className="text-xl" />

      <h1 className="mt-14 text-2xl font-bold">
        {mode === 'login' ? 'Sign in' : 'Create your account'}
      </h1>
      <p className="mt-2 text-sm text-slate-500">
        {mode === 'login'
          ? 'Use the email and password you registered with.'
          : 'After you register, an admin gives you access to an event.'}
      </p>

      <form className="mt-8 space-y-4" onSubmit={submit}>
        <div>
          <label className="field-label">Email</label>
          <input
            className="field-input"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="field-label">Password</label>
          <input
            className="field-input"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button className="btn-primary w-full" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
      </form>

      <button
        type="button"
        className="mt-6 text-sm font-medium text-brand"
        onClick={() => {
          setMode(mode === 'login' ? 'register' : 'login')
          setError('')
        }}
      >
        {mode === 'login'
          ? 'New here? Create an account'
          : 'Already have an account? Sign in'}
      </button>
    </div>
  )
}
