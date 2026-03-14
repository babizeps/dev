import { useState } from 'react'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../store/auth.store'

const s: Record<string, React.CSSProperties> = {
  form: { display: 'flex', flexDirection: 'column', gap: 12, width: 320 },
  input: { padding: '8px 12px', border: '1px solid #ddd', borderRadius: 6, fontSize: 14, outline: 'none' },
  btn: { padding: '10px 0', background: '#37352f', color: '#fff', border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer', fontWeight: 500 },
  err: { color: '#e03e3e', fontSize: 13 },
}

export default function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const setUser = useAuthStore((s) => s.setUser)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const { user } = await authApi.register(email, password)
      setUser(user)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    }
  }

  return (
    <form style={s.form} onSubmit={submit}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Create account</h2>
      {error && <span style={s.err}>{error}</span>}
      <input style={s.input} type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input style={s.input} type="password" placeholder="Password (min. 8 chars)" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
      <button style={s.btn} type="submit">Sign up</button>
      <button type="button" style={{ ...s.btn, background: 'transparent', color: '#37352f', border: '1px solid #ddd' }} onClick={onSwitch}>
        Already have an account? Log in
      </button>
    </form>
  )
}
