import { useState, useEffect } from 'react'
import { ShieldCheck, ShieldOff, Search, UserPlus, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
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
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [inviteRole, setInviteRole] = useState('pilot')
  const [inviteRequiredNotes, setInviteRequiredNotes] = useState('')
  const [inviteToken, setInviteToken] = useState('')
  const [copied, setCopied] = useState(false)

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

  const handleInvite = async () => {
    try {
      const res = await api.post('/api/v1/auth/invite', {
        email: inviteEmail,
        role: inviteRole,
        display_name: inviteName,
        required_notes: inviteRequiredNotes || undefined,
      })
      setInviteToken(res.data.invite_token)
    } catch { /* silent */ }
  }

  const handleCopy = () => {
    const baseUrl = window.location.origin
    const link = `${baseUrl}/accept-invite?token=${inviteToken}`
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const filtered = search
    ? users.filter(u => u.display_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
    : users

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Permissions</h1>
          <p className="mt-1 text-sm text-muted-foreground">{users.length} users · Manage PII clearance</p>
        </div>
        <Button onClick={() => { setInviteEmail(''); setInviteRole('pilot'); setInviteToken(''); setShowInvite(true) }}>
          <UserPlus className="mr-2 h-4 w-4" /> Invite User
        </Button>
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

      {/* Invite Dialog */}
      <Dialog open={showInvite} onOpenChange={(open) => { setShowInvite(open); if (!open) setInviteToken('') }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Invite User</DialogTitle>
            <DialogDescription>
              Send an invite link to a pilot, dispatcher, or mechanic. They'll create their own account and join your organization.
            </DialogDescription>
          </DialogHeader>

          {!inviteToken ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Full Name</label>
                <Input placeholder="Jane Pilot" value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <Input type="email" placeholder="pilot@example.com" value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                  <option value="pilot">Pilot</option>
                  <option value="dispatcher">Dispatcher</option>
                  <option value="mechanic">Mechanic</option>
                  <option value="ops_manager">Ops Manager</option>
                  <option value="admin">Admin</option>
                  <option value="readonly">Read Only</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Required Info <span className="text-muted-foreground">(optional)</span></label>
                <textarea className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="E.g. 'Must provide emergency contact and date of birth before first flight'"
                  value={inviteRequiredNotes} onChange={(e) => setInviteRequiredNotes(e.target.value)} />
              </div>
              <div className="flex justify-end">
                <Button onClick={handleInvite} disabled={!inviteEmail || !inviteName}>Generate Invite</Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-green-500">Invite created! Copy this link and send it to the user:</p>
              <div className="flex items-center gap-2 rounded-md border border-border bg-muted p-2">
                <code className="flex-1 truncate text-xs">
                  {window.location.origin}/accept-invite?token={inviteToken.slice(0, 20)}...
                </code>
                <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={handleCopy}>
                  {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Token expires in 48 hours. The user will join your organization with the role you selected.
              </p>
              <div className="flex justify-end">
                <Button variant="outline" onClick={() => { setShowInvite(false); setInviteToken('') }}>Done</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
