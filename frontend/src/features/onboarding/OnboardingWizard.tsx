import { useState, useEffect, type FormEvent } from 'react'
import { Plane, Users, ClipboardCheck, CheckCircle, ArrowRight, X, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import api from '@/lib/api'
import { useAuthContext } from '@/features/auth/AuthContext'

interface OnboardingStep {
  id: string
  label: string
  description: string
}

interface OnboardingStatus {
  finished: boolean
  current_step: string
  completed_steps: string[]
  steps: OnboardingStep[]
  progress_pct: number
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  welcome: <Plane className="h-5 w-5" />,
  aircraft: <Plane className="h-5 w-5" />,
  crew: <Users className="h-5 w-5" />,
  compliance: <ClipboardCheck className="h-5 w-5" />,
  complete: <CheckCircle className="h-5 w-5" />,
}

const DISMISSED_KEY = 'pararig_onboarding_dismissed'

export default function OnboardingWizard() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === 'true',
  )
  const { token } = useAuthContext()

  // Welcome step
  const [orgName, setOrgName] = useState('')
  const [orgTimezone, setOrgTimezone] = useState('America/Nassau')

  // Aircraft step
  const [tailNumber, setTailNumber] = useState('')
  const [aircraftMake, setAircraftMake] = useState('')
  const [aircraftModel, setAircraftModel] = useState('')
  const [aircraftYear, setAircraftYear] = useState(new Date().getFullYear().toString())
  const [homeAirport, setHomeAirport] = useState('')

  // Crew step
  const [crewFirstName, setCrewFirstName] = useState('')
  const [crewLastName, setCrewLastName] = useState('')
  const [crewEmail, setCrewEmail] = useState('')
  const [crewRole, setCrewRole] = useState('captain')

  useEffect(() => {
    if (!token) return
    setError('')
    api
      .get<OnboardingStatus>('/api/v1/onboarding/status')
      .then((res) => {
        setStatus(res.data)
        // Pre-fill org name if user's org already exists
        if (res.data.current_step === 'welcome' && !res.data.finished) {
          // Optionally load existing org name from user context
        }
      })
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [token])

  // Don't render if dismissed, loading, no status, or already finished
  if (loading || dismissed || !status || status.finished) return null

  const stepIndex = status.steps.findIndex((s) => s.id === status.current_step)

  const advanceStep = (stepId: string) => {
    setStatus((prev) =>
      prev
        ? {
            ...prev,
            completed_steps: [...prev.completed_steps, stepId],
            progress_pct: Math.round(
              ((prev.completed_steps.length + 1) / prev.steps.length) * 100,
            ),
          }
        : prev,
    )
  }

  // ── Welcome handler ──────────────────────────────────────────────
  const handleWelcome = async () => {
    setError('')
    if (!orgName.trim()) {
      setError('Please enter your organization name.')
      return
    }
    setSubmitting(true)
    try {
      const res = await api.post('/api/v1/onboarding/step', null, {
        params: { step_id: 'welcome' },
        data: {
          org_name: orgName.trim(),
          timezone: orgTimezone,
        },
      })
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              current_step: res.data.current_step,
              completed_steps: [...prev.completed_steps, 'welcome'],
              progress_pct: res.data.progress_pct,
              finished: res.data.finished,
            }
          : prev,
      )
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to save organization name. Please try again.'
      setError(detail)
    }
    setSubmitting(false)
  }

  // ── Aircraft handler ─────────────────────────────────────────────
  const handleAircraft = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!homeAirport.trim()) {
      setError('Please enter a home airport (ICAO code, e.g. MYNN).')
      return
    }
    if (!aircraftYear || isNaN(Number(aircraftYear)) || Number(aircraftYear) < 1900) {
      setError('Please enter a valid aircraft year.')
      return
    }
    setSubmitting(true)
    try {
      // 1. Create the aircraft via the dedicated endpoint
      await api.post('/api/v1/aircraft', {
        tail_number: tailNumber.trim().toUpperCase(),
        make: aircraftMake.trim(),
        model: aircraftModel.trim(),
        year: Number(aircraftYear),
        base: homeAirport.trim().toUpperCase(),
        home_airport: homeAirport.trim().toUpperCase(),
        country_reg: 'BS',
        category: 'single_engine_turboprop',
        status: 'active',
      })

      // 2. Advance the onboarding step
      const res = await api.post('/api/v1/onboarding/step', null, {
        params: { step_id: 'aircraft' },
        data: {
          tail_number: tailNumber.trim().toUpperCase(),
          make: aircraftMake.trim(),
          model: aircraftModel.trim(),
        },
      })
      advanceStep('aircraft')
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              current_step: res.data.current_step,
              progress_pct: res.data.progress_pct,
              finished: res.data.finished,
            }
          : prev,
      )
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to add aircraft. Please try again.'
      setError(detail)
    }
    setSubmitting(false)
  }

  // ── Crew handler ─────────────────────────────────────────────────
  const handleCrew = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!crewFirstName.trim() || !crewLastName.trim()) {
      setError('Please enter the crew member\'s first and last name.')
      return
    }
    setSubmitting(true)
    try {
      // 1. Create the crew member via the dedicated endpoint
      await api.post('/api/v1/crew', {
        first_name: crewFirstName.trim(),
        last_name: crewLastName.trim(),
        email: crewEmail.trim() || null,
        role: crewRole,
      })

      // 2. Advance the onboarding step
      const res = await api.post('/api/v1/onboarding/step', null, {
        params: { step_id: 'crew' },
        data: {
          first_name: crewFirstName.trim(),
          last_name: crewLastName.trim(),
          email: crewEmail.trim(),
          role: crewRole,
        },
      })
      advanceStep('crew')
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              current_step: res.data.current_step,
              progress_pct: res.data.progress_pct,
              finished: res.data.finished,
            }
          : prev,
      )
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to add crew member. Please try again.'
      setError(detail)
    }
    setSubmitting(false)
  }

  // ── Compliance handler ───────────────────────────────────────────
  const handleCompliance = async () => {
    setError('')
    setSubmitting(true)
    try {
      const res = await api.post('/api/v1/onboarding/step', null, {
        params: { step_id: 'compliance' },
        data: { skipped: true },
      })
      advanceStep('compliance')
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              current_step: res.data.current_step,
              progress_pct: res.data.progress_pct,
              finished: res.data.finished,
            }
          : prev,
      )
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to save progress.'
      setError(detail)
    }
    setSubmitting(false)
  }

  // ── Finish / Dismiss ─────────────────────────────────────────────
  const handleFinish = async () => {
    setError('')
    setSubmitting(true)
    try {
      await api.post('/api/v1/onboarding/step', null, {
        params: { step_id: 'complete' },
        data: {},
      })
    } catch {
      // Best effort — wizard can still dismiss
    }
    localStorage.setItem(DISMISSED_KEY, 'true')
    setDismissed(true)
    setSubmitting(false)
  }

  const handleSkip = async () => {
    try {
      await api.post('/api/v1/onboarding/skip')
    } catch {
      // Best effort
    }
    localStorage.setItem(DISMISSED_KEY, 'true')
    setDismissed(true)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <Card className="mx-4 w-full max-w-lg shadow-2xl">
        <CardHeader className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 top-4 h-6 w-6 text-muted-foreground"
            onClick={handleSkip}
            aria-label="Skip onboarding"
          >
            <X className="h-4 w-4" />
          </Button>
          <CardTitle className="flex items-center gap-2">
            {STEP_ICONS[status.current_step]}
            {status.current_step === 'complete' ? 'You\'re all set!' : 'Welcome to ParaRig Ops'}
          </CardTitle>
          <CardDescription>
            {status.current_step === 'complete'
              ? 'Your organization is ready to go.'
              : 'Let\'s get your organization set up in a few quick steps.'}
          </CardDescription>

          {/* Progress bar */}
          {status.current_step !== 'complete' && (
            <>
              <div className="mt-3 flex gap-1">
                {status.steps.map((s) => (
                  <div
                    key={s.id}
                    className={`h-1.5 flex-1 rounded-full transition-colors ${
                      status.completed_steps.includes(s.id) || s.id === status.current_step
                        ? 'bg-brand-500'
                        : 'bg-muted'
                    }`}
                  />
                ))}
              </div>
              <p className="mt-1 text-right text-xs text-muted-foreground">
                Step {stepIndex + 1} of {status.steps.length}
              </p>
            </>
          )}
        </CardHeader>

        <CardContent>
          {/* ── Inline error ──────────────────────────────────── */}
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}

          {/* ── Welcome ───────────────────────────────────────── */}
          {status.current_step === 'welcome' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                ParaRig Ops helps you manage your fleet, schedule flights, track maintenance,
                stay compliant, and monitor your finances — all from one place.
              </p>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="org-name">
                  Organization Name
                </label>
                <Input
                  id="org-name"
                  placeholder="ParaRig Dynamics"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="org-timezone">
                  Timezone
                </label>
                <select
                  id="org-timezone"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                  value={orgTimezone}
                  onChange={(e) => setOrgTimezone(e.target.value)}
                >
                  <option value="America/Nassau">America/Nassau (UTC-5)</option>
                  <option value="America/New_York">America/New York (UTC-5)</option>
                  <option value="America/Chicago">America/Chicago (UTC-6)</option>
                  <option value="America/Denver">America/Denver (UTC-7)</option>
                  <option value="America/Los_Angeles">America/Los Angeles (UTC-8)</option>
                  <option value="America/Anchorage">America/Anchorage (UTC-9)</option>
                  <option value="America/Phoenix">America/Phoenix (UTC-7)</option>
                  <option value="America/Sao_Paulo">America/Sao Paulo (UTC-3)</option>
                  <option value="Europe/London">Europe/London (UTC+0)</option>
                  <option value="Europe/Paris">Europe/Paris (UTC+1)</option>
                  <option value="Asia/Dubai">Asia/Dubai (UTC+4)</option>
                  <option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option>
                </select>
              </div>
              <Button onClick={handleWelcome} disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="mr-2 h-4 w-4" />
                )}
                Get Started
              </Button>
            </div>
          )}

          {/* ── Add Aircraft ──────────────────────────────────── */}
          {status.current_step === 'aircraft' && (
            <form onSubmit={handleAircraft} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Register your first aircraft to begin tracking.
              </p>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="tail-number">Tail Number</label>
                <Input
                  id="tail-number"
                  placeholder="C6-PRD"
                  value={tailNumber}
                  onChange={(e) => setTailNumber(e.target.value.toUpperCase())}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="aircraft-make">Make</label>
                  <Input
                    id="aircraft-make"
                    placeholder="Cessna"
                    value={aircraftMake}
                    onChange={(e) => setAircraftMake(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="aircraft-model">Model</label>
                  <Input
                    id="aircraft-model"
                    placeholder="208B Grand Caravan"
                    value={aircraftModel}
                    onChange={(e) => setAircraftModel(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="aircraft-year">Year</label>
                  <Input
                    id="aircraft-year"
                    type="number"
                    placeholder={new Date().getFullYear().toString()}
                    value={aircraftYear}
                    onChange={(e) => setAircraftYear(e.target.value)}
                    min={1900}
                    max={2030}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="home-airport">Home Airport (ICAO)</label>
                  <Input
                    id="home-airport"
                    placeholder="MYNN"
                    value={homeAirport}
                    onChange={(e) => setHomeAirport(e.target.value.toUpperCase())}
                    maxLength={4}
                    minLength={3}
                    required
                  />
                </div>
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plane className="mr-2 h-4 w-4" />
                )}
                {submitting ? 'Adding Aircraft...' : 'Add Aircraft & Continue'}
              </Button>
            </form>
          )}

          {/* ── Add Crew ──────────────────────────────────────── */}
          {status.current_step === 'crew' && (
            <form onSubmit={handleCrew} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Add your first crew member.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="crew-first-name">First Name</label>
                  <Input
                    id="crew-first-name"
                    placeholder="James"
                    value={crewFirstName}
                    onChange={(e) => setCrewFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="crew-last-name">Last Name</label>
                  <Input
                    id="crew-last-name"
                    placeholder="Mitchell"
                    value={crewLastName}
                    onChange={(e) => setCrewLastName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="crew-email">Email</label>
                <Input
                  id="crew-email"
                  type="email"
                  placeholder="james@pararig.aero"
                  value={crewEmail}
                  onChange={(e) => setCrewEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="crew-role">Role</label>
                <select
                  id="crew-role"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                  value={crewRole}
                  onChange={(e) => setCrewRole(e.target.value)}
                >
                  <option value="captain">Captain</option>
                  <option value="first_officer">First Officer</option>
                  <option value="mechanic">Mechanic</option>
                  <option value="dispatcher">Dispatcher</option>
                </select>
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Users className="mr-2 h-4 w-4" />
                )}
                {submitting ? 'Adding Crew...' : 'Add Crew & Continue'}
              </Button>
            </form>
          )}

          {/* ── Compliance ────────────────────────────────────── */}
          {status.current_step === 'compliance' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Keep your compliance documents organized. You can upload them later
                from the Compliance section — for now, let's mark this as ready.
              </p>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <span className="text-brand-400">•</span> Airworthiness Certificate
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-brand-400">•</span> Aircraft Insurance
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-brand-400">•</span> Operating Specifications
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-brand-400">•</span> Crew Licenses & Medicals
                </li>
              </ul>
              <Button onClick={handleCompliance} disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="mr-2 h-4 w-4" />
                )}
                {submitting ? 'Saving...' : 'Mark as Ready'}
              </Button>
            </div>
          )}

          {/* ── Complete / Summary ────────────────────────────── */}
          {status.current_step === 'complete' && (
            <div className="space-y-5 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <div>
                <p className="text-lg font-medium">You're all set!</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Your organization is ready. Here's what you set up:
                </p>
              </div>

              <ul className="space-y-2 text-left text-sm">
                {status.completed_steps.includes('welcome') && (
                  <li className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Organization configured</span>
                  </li>
                )}
                {status.completed_steps.includes('aircraft') && (
                  <li className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Aircraft registered: <strong>{tailNumber || 'added'}</strong></span>
                  </li>
                )}
                {status.completed_steps.includes('crew') && (
                  <li className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Crew member added: <strong>{crewFirstName} {crewLastName}</strong></span>
                  </li>
                )}
                {status.completed_steps.includes('compliance') && (
                  <li className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Compliance section acknowledged</span>
                  </li>
                )}
              </ul>

              <Button onClick={handleFinish} disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="mr-2 h-4 w-4" />
                )}
                Go to Dashboard
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
