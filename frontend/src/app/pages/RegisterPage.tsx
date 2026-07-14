import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PlaneTakeoff, Key } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthContext } from '@/features/auth/AuthContext'

export default function RegisterPage() {
  const [inviteCode, setInviteCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuthContext()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!inviteCode) { setError('Invite code is required'); return }
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }

    setLoading(true)
    try {
      await register({
        orgName: 'Org',
        orgSlug: `org-${Date.now()}`,
        email, password, displayName,
        inviteCode,
      })
      navigate('/', { replace: true })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-4 flex items-center justify-center gap-2">
            <PlaneTakeoff className="h-8 w-8 text-brand-400" />
            <span className="text-2xl font-bold">ParaRig Ops</span>
          </div>
          <CardTitle className="text-xl">Create Account</CardTitle>
          <CardDescription>Enter your invite code to get started.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/15 px-3 py-2 text-sm text-destructive">{error}</div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Invite Code</label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input className="pl-9 font-mono tracking-wider uppercase" placeholder="XXXX-XXXX"
                  value={inviteCode} onChange={(e) => setInviteCode(e.target.value.toUpperCase())} required />
              </div>
              <p className="text-xs text-muted-foreground">Provided by your organization administrator.</p>
            </div>

            {inviteCode && (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Your Name</label>
                  <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Confirm Password</label>
                  <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
                </div>
              </>
            )}

            <Button type="submit" className="w-full" disabled={loading || !inviteCode}>
              {loading ? 'Creating account…' : 'Register'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:underline">Sign in</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
