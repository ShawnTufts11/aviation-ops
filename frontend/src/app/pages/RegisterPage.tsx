import { useState, type FormEvent, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PlaneTakeoff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthContext } from '@/features/auth/AuthContext'

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 100)
}

export default function RegisterPage() {
  const [orgName, setOrgName] = useState('')
  const [orgSlug, setOrgSlug] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuthContext()
  const navigate = useNavigate()

  const handleOrgNameChange = useCallback(
    (value: string) => {
      setOrgName(value)
      if (!slugManuallyEdited) {
        setOrgSlug(slugify(value))
      }
    },
    [slugManuallyEdited],
  )

  const handleSlugChange = useCallback((value: string) => {
    setSlugManuallyEdited(true)
    setOrgSlug(slugify(value))
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!orgSlug) {
      setError('Organization slug is required')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setLoading(true)
    try {
      await register({ orgName, orgSlug, email, password, displayName })
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Registration failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-4 flex items-center justify-center gap-2">
            <PlaneTakeoff className="h-8 w-8 text-brand-400" />
            <span className="text-2xl font-bold">ParaRig Ops</span>
          </div>
          <CardTitle className="text-xl">Create your organization</CardTitle>
          <CardDescription>
            Set up your aviation operations account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/15 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label
                htmlFor="orgName"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Organization Name
              </label>
              <Input
                id="orgName"
                type="text"
                placeholder="ParaRig Dynamics"
                value={orgName}
                onChange={(e) => handleOrgNameChange(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="orgSlug"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                URL Slug
              </label>
              <Input
                id="orgSlug"
                type="text"
                placeholder="pararig-dynamics"
                value={orgSlug}
                onChange={(e) => handleSlugChange(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Auto-generated from organization name. Edit to customize.
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="displayName"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Your Name
              </label>
              <Input
                id="displayName"
                type="text"
                placeholder="Shawn"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="name@pararig.aero"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="Min. 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="confirm"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Confirm Password
              </label>
              <Input
                id="confirm"
                type="password"
                placeholder="••••••••"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creating account…' : 'Create organization'}
            </Button>
          </form>

          <div className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:underline">
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
