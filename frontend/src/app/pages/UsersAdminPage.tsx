import { useState, useEffect } from 'react'
import { ShieldCheck, ShieldOff, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'

interface User {
  id: string; email: string; display_name: string
  role: string; is_active: boolean; pii_clearance: boolean
  last_login: string | null
}

const ROLE_COLORS: Record<string, string> = {
  super_admin: 'bg-purple-500/10 text-purple-500',
  ops_manager: 'bg-blue-500/10 text-blue-500',
  admin: 'bg-sky-500/10 text-sky-500',
  mechanic: 'bg-amber-500/10 text-amber-500',
  pilot: 'bg-green-500/10 text-green-500',
  dispatcher: 'bg-orange-500/10 text-orange-500',
}

export default function UsersAdminPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const fetchUsers = async () => {
    try {
      const res = await api.get('/api/v1/users')
      setUsers(res.data)
    } catch { /* silent */ }
    setLoading(false)
  }

  useEffect(() => { fetchUsers() }, [])

  const togglePII = async (u: User) => {
    try {
      await api.patch(`/api/v1/users/${u.id}/permissions`, { pii_clearance: !u.pii_clearance })
      await fetchUsers()
    } catch { /* silent */ }
  }

  const filtered = search
    ? users.filter(u => u.display_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
    : users

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Permissions</h1>
        <p className="mt-1 text-sm text-muted-foreground">{users.length} users · Manage PII clearance</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-9" placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => (
          <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-12 rounded bg-muted" /></CardContent></Card>
        ))}</div>
      ) : (
        <div className="space-y-3">
          {filtered.map((u) => (
            <Card key={u.id} className="border-border/50">
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{u.display_name}</span>
                    <Badge variant="outline" className={ROLE_COLORS[u.role] || ''}>
                      {u.role.replace('_', ' ')}
                    </Badge>
                    {!u.is_active && <Badge variant="outline" className="text-red-500">INACTIVE</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{u.email}</p>
                </div>
                <Button
                  variant={u.pii_clearance ? 'default' : 'outline'}
                  size="sm"
                  className={u.pii_clearance ? 'bg-green-600 hover:bg-green-700' : ''}
                  onClick={() => togglePII(u)}
                >
                  {u.pii_clearance ? (
                    <><ShieldCheck className="mr-1.5 h-3.5 w-3.5" /> PII Access</>
                  ) : (
                    <><ShieldOff className="mr-1.5 h-3.5 w-3.5" /> No PII</>
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
