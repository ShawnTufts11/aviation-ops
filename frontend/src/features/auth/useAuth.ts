import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type { User, LoginResponse, RegisterResponse } from '@/types'

interface AuthContext {
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
  }) => Promise<void>
  logout: () => void
}

export function useAuth(): AuthContext {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [organization, setOrganization] = useState<{
    id: string
    name: string
    slug: string
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('pararig_token')
    const storedUser = localStorage.getItem('pararig_user')
    const storedOrg = localStorage.getItem('pararig_org')
    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser) as User)
        if (storedOrg) {
          setOrganization(JSON.parse(storedOrg))
        }
      } catch {
        localStorage.removeItem('pararig_token')
        localStorage.removeItem('pararig_user')
        localStorage.removeItem('pararig_org')
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<LoginResponse>('/api/v1/auth/login', {
      email,
      password,
    })
    const { access_token, user: u } = res.data
    localStorage.setItem('pararig_token', access_token)
    localStorage.setItem('pararig_user', JSON.stringify(u))
    setToken(access_token)
    setUser(u)
  }, [])

  const register = useCallback(
    async (opts: {
      orgName: string
      orgSlug: string
      email: string
      password: string
      displayName: string
      inviteCode?: string
    }) => {
      const res = await api.post<RegisterResponse>('/api/v1/auth/register', {
        org_name: opts.orgName,
        org_slug: opts.orgSlug,
        email: opts.email,
        password: opts.password,
        display_name: opts.displayName,
        invite_code: opts.inviteCode || undefined,
      })
      const { access_token, user: u, organization: org } = res.data
      localStorage.setItem('pararig_token', access_token)
      localStorage.setItem('pararig_user', JSON.stringify(u))
      localStorage.setItem('pararig_org', JSON.stringify(org))
      setToken(access_token)
      setUser(u)
      setOrganization({ id: org.id, name: org.name, slug: org.slug })
    },
    [],
  )

  const logout = useCallback(() => {
    localStorage.removeItem('pararig_token')
    localStorage.removeItem('pararig_user')
    localStorage.removeItem('pararig_org')
    setToken(null)
    setUser(null)
    setOrganization(null)
  }, [])

  return {
    user,
    token,
    organization,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    register,
    logout,
  } as const
}
