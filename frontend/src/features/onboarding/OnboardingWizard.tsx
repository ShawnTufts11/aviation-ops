import { useState, useEffect, type FormEvent } from 'react'
import { Plane, Users, ClipboardCheck, CheckCircle, ArrowRight, X } from 'lucide-react'
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

export default function OnboardingWizard() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const { token } = useAuthContext()

  // Step-specific form data
  const [tailNumber, setTailNumber] = useState('')
  const [aircraftMake, setAircraftMake] = useState('')
  const [aircraftModel, setAircraftModel] = useState('')
  const [crewName, setCrewName] = useState('')
  const [crewEmail, setCrewEmail] = useState('')
  const [crewRole, setCrewRole] = useState('captain')

  useEffect(() => {
    if (!token) return
    api
      .get<OnboardingStatus>('/api/v1/onboarding/status')
      .then((res) => setStatus(res.data))
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [token])

  if (loading || dismissed || !status || status.finished) return null

  const completeStep = async (stepId: string, stepData: Record<string, unknown> = {}) => {
    setSubmitting(true)
    try {
      const res = await api.post(`/api/v1/onboarding/step?step_id=${stepId}`, { step_data: stepData })
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              current_step: res.data.current_step,
              completed_steps: [...prev.completed_steps, stepId],
              progress_pct: res.data.progress_pct,
              finished: res.data.finished,
            }
          : prev,
      )
    } catch {
      // ignore
    }
    setSubmitting(false)
  }

  const handleWelcome = async () => {
    await completeStep('welcome')
  }

  const handleAircraft = async (e: FormEvent) => {
    e.preventDefault()
    await completeStep('aircraft', {
      tail_number: tailNumber,
      make: aircraftMake,
      model: aircraftModel,
    })
  }

  const handleCrew = async (e: FormEvent) => {
    e.preventDefault()
    await completeStep('crew', {
      name: crewName,
      email: crewEmail,
      role: crewRole,
    })
  }

  const handleCompliance = async () => {
    await completeStep('compliance')
  }

  const handleFinish = async () => {
    await completeStep('complete', {})
  }

  const stepIndex = status.steps.findIndex((s) => s.id === status.current_step)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <Card className="mx-4 w-full max-w-lg shadow-2xl">
        <CardHeader className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 top-4 h-6 w-6 text-muted-foreground"
            onClick={async () => {
              await api.post('/api/v1/onboarding/skip')
              setDismissed(true)
            }}
          >
            <X className="h-4 w-4" />
          </Button>
          <CardTitle className="flex items-center gap-2">
            {STEP_ICONS[status.current_step]}
            Welcome to ParaRig Ops
          </CardTitle>
          <CardDescription>
            Let's get your organization set up in a few quick steps.
          </CardDescription>

          {/* Progress bar */}
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
        </CardHeader>

        <CardContent>
          {/* Welcome */}
          {status.current_step === 'welcome' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                ParaRig Ops helps you manage your fleet, schedule flights, track maintenance,
                stay compliant, and monitor your finances — all from one place.
              </p>
              <p className="text-sm text-muted-foreground">
                We'll walk you through adding your first aircraft, crew members, and compliance
                documents in about 2 minutes.
              </p>
              <Button onClick={handleWelcome} disabled={submitting} className="w-full">
                Get Started <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Add Aircraft */}
          {status.current_step === 'aircraft' && (
            <form onSubmit={handleAircraft} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Register your first aircraft to begin tracking.
              </p>
              <div className="space-y-2">
                <label className="text-sm font-medium">Tail Number</label>
                <Input
                  placeholder="C6-PRD"
                  value={tailNumber}
                  onChange={(e) => setTailNumber(e.target.value.toUpperCase())}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Make</label>
                  <Input
                    placeholder="Cessna"
                    value={aircraftMake}
                    onChange={(e) => setAircraftMake(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Model</label>
                  <Input
                    placeholder="208B Grand Caravan"
                    value={aircraftModel}
                    onChange={(e) => setAircraftModel(e.target.value)}
                    required
                  />
                </div>
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                Add Aircraft & Continue
              </Button>
            </form>
          )}

          {/* Add Crew */}
          {status.current_step === 'crew' && (
            <form onSubmit={handleCrew} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Add your first crew member.
              </p>
              <div className="space-y-2">
                <label className="text-sm font-medium">Full Name</label>
                <Input
                  placeholder="James Mitchell"
                  value={crewName}
                  onChange={(e) => setCrewName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <Input
                  type="email"
                  placeholder="james@pararig.aero"
                  value={crewEmail}
                  onChange={(e) => setCrewEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <select
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
                Add Crew & Continue
              </Button>
            </form>
          )}

          {/* Compliance */}
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
                Mark as Ready
              </Button>
            </div>
          )}

          {/* Complete */}
          {status.current_step === 'complete' && (
            <div className="space-y-4 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <p className="text-lg font-medium">You're all set!</p>
              <p className="text-sm text-muted-foreground">
                Your organization is ready. You can add more aircraft, crew, and
                documents from the sidebar at any time.
              </p>
              <Button onClick={handleFinish} disabled={submitting} className="w-full">
                Go to Dashboard
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
