import { createContext, useContext, type ReactNode } from 'react'
import { useAuth } from './useAuth'
import type { User } from '@/types'

interface AuthContextValue {
  user: User | null
  token: string | null
  organization: { id: string; name: string; slug: string } | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (opts: {
    orgName: string
    orgSlug: string
    email: string
    password: string
    displayName: string
    inviteCode?: string
  }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return ctx
}
