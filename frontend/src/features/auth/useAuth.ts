import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type { User } from '@/types'

interface AuthContext {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (orgName: string, email: string, password: string) => Promise<void>
  logout: () => void
}

export function useAuth(): AuthContext {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('pararig_token')
    const storedUser = localStorage.getItem('pararig_user')
    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser) as User)
      } catch {
        localStorage.removeItem('pararig_token')
        localStorage.removeItem('pararig_user')
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ user: User; token: string }>('/auth/login', {
      email,
      password,
    })
    const { user: u, token: t } = res.data
    localStorage.setItem('pararig_token', t)
    localStorage.setItem('pararig_user', JSON.stringify(u))
    setToken(t)
    setUser(u)
  }, [])

  const register = useCallback(
    async (orgName: string, email: string, password: string) => {
      const res = await api.post<{ user: User; token: string }>(
        '/auth/register',
        {
          organization_name: orgName,
          email,
          password,
        },
      )
      const { user: u, token: t } = res.data
      localStorage.setItem('pararig_token', t)
      localStorage.setItem('pararig_user', JSON.stringify(u))
      setToken(t)
      setUser(u)
    },
    [],
  )

  const logout = useCallback(() => {
    localStorage.removeItem('pararig_token')
    localStorage.removeItem('pararig_user')
    setToken(null)
    setUser(null)
  }, [])

  return {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    register,
    logout,
  } as const
}
