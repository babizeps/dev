import { createBrowserRouter, Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth.store'
import AuthPage from '../pages/AuthPage'
import WorkspacePage from '../pages/WorkspacePage'
import PageDetailPage from '../pages/PageDetailPage'
import AppLayout from '../components/layout/AppLayout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuthStore()
  if (isLoading) return <div style={{ padding: 32, color: '#999' }}>Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export const router = createBrowserRouter([
  { path: '/login', element: <AuthPage /> },
  {
    path: '/',
    element: (
      <PrivateRoute>
        <AppLayout />
      </PrivateRoute>
    ),
    children: [
      { index: true, element: <WorkspacePage /> },
      { path: ':pageId', element: <PageDetailPage /> },
    ],
  },
])
