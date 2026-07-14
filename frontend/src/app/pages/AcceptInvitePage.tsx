import { useState, type FormEvent } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { UserPlus, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import api from '@/lib/api'

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [accepted, setAccepted] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token) { setError('Invalid invite link'); return }
    setSubmitting(true)
    setError('')
    try {
      await api.post('/api/v1/auth/accept-invite', { token, display_name: name, password })
      setAccepted(true)
      setTimeout(() => navigate('/'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invite expired or invalid')
    }
    setSubmitting(false)
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
            <XCircle className="h-12 w-12 text-red-500" />
            <p className="text-lg font-medium">Invalid Link</p>
            <p className="text-sm text-muted-foreground">No invite token found.</p>
            <Button onClick={() => navigate('/login')}>Go to Login</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (accepted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <p className="text-lg font-medium">Account Created!</p>
            <p className="text-sm text-muted-foreground">Redirecting to your dashboard...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-brand-500/10">
            <UserPlus className="h-6 w-6 text-brand-400" />
          </div>
          <CardTitle className="text-xl">Accept Invitation</CardTitle>
          <p className="text-sm text-muted-foreground">Set up your account to join the organization.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Your Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="John Doe" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required minLength={8} placeholder="At least 8 characters" />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Creating Account...' : 'Accept & Join'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
