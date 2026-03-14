import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router/index'
import { useAuthStore } from './store/auth.store'
import { authApi } from './api/auth'

export default function App() {
  const { setUser, setLoading } = useAuthStore()

  useEffect(() => {
    authApi.me()
      .then(({ user }) => setUser(user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  return <RouterProvider router={router} />
}
