import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import LoginForm from '../components/auth/LoginForm'
import RegisterForm from '../components/auth/RegisterForm'
import { useAuthStore } from '../store/auth.store'

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const user = useAuthStore((s) => s.user)

  if (user) return <Navigate to="/" replace />

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#f7f7f5' }}>
      <div style={{ background: '#fff', padding: 40, borderRadius: 12, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
        <div style={{ fontSize: 28, marginBottom: 24, textAlign: 'center' }}>📝</div>
        {mode === 'login'
          ? <LoginForm onSwitch={() => setMode('register')} />
          : <RegisterForm onSwitch={() => setMode('login')} />}
      </div>
    </div>
  )
}
