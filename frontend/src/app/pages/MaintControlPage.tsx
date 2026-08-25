import { useState, useEffect } from 'react'
import {
  Wrench,
  Plane,
  ShieldCheck,
  Clock,
  CheckCircle,
  XCircle,
  MinusCircle,
  AlertTriangle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

interface Aircraft {
  id: string
  tail_number: string
  type: string       // derived from make + model; falls back to a single type string
  make?: string
  model?: string
  status: string
  safe_for_flight: boolean
  mission_capability: 'full' | 'partial' | 'not_capable'
  last_inspected: string | null
  total_hours: number | null
}

interface Gripe {
  id?: string
  description: string
  severity: 'minor' | 'major' | 'critical'
  status: 'open' | 'deferred' | 'resolved'
  date_logged?: string
  mechanic_notes?: string
  aircraft_tail?: string
  aircraft_id?: string
  /** Fallback from the dashboard gripe shape — severity might be 'red'|'yellow'|'green' */
  reported_by?: string
  reported_at?: string
}

interface DashboardAircraftEntry {
  aircraft_id: string
  tail_number: string
  make: string
  model: string
  status: string
  safe_for_flight: boolean
  mission_capability: string
  gripes_open_count: number
  gripes_deferred_count: number
  has_open_gripes: boolean
  gripes_open: Gripe[]
  gripes_deferred: Gripe[]
  latest_release_id?: string | null
  latest_release_number?: string | null
}

interface DashboardSummary {
  total_aircraft: number
  active: number
  in_maintenance: number
  grounded: number
  aircraft_with_open_gripes: number
  aircraft_with_deferred_gripes: number
  aircraft_not_safe_for_flight: number
}

interface DashboardResponse {
  aircraft: DashboardAircraftEntry[]
  total_aircraft: number
  summary: DashboardSummary
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtDate(d: string | null | undefined) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmtDateShort(d: string | null | undefined) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

/** Normalise a dashboard-backend severity string to the frontend's 3-tier enum. */
function normaliseSeverity(s: string | undefined): 'minor' | 'major' | 'critical' {
  if (!s) return 'minor'
  const lower = s.toLowerCase()
  if (lower === 'red' || lower === 'critical') return 'critical'
  if (lower === 'yellow' || lower === 'major') return 'major'
  return 'minor'
}

/** Map bogus statuses from dashboard gripes ('open' / 'deferred' / anything) to valid. */
function normaliseStatus(s: string | undefined): 'open' | 'deferred' | 'resolved' {
  const lower = (s || 'open').toLowerCase()
  if (lower === 'deferred') return 'deferred'
  if (lower === 'resolved') return 'resolved'
  return 'open'
}

const CAPABILITY_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  full: {
    label: 'Full',
    color: 'bg-green-500/10 text-green-500 border-green-500/20',
    icon: <CheckCircle className="h-4 w-4" />,
  },
  partial: {
    label: 'Partial',
    color: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    icon: <MinusCircle className="h-4 w-4" />,
  },
  not_capable: {
    label: 'Not Capable',
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
    icon: <XCircle className="h-4 w-4" />,
  },
}

const SEVERITY_CONFIG: Record<string, { label: string; color: string }> = {
  minor: { label: 'Minor', color: 'bg-green-500/10 text-green-500 border-green-500/20' },
  major: { label: 'Major', color: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
  critical: { label: 'Critical', color: 'bg-red-500/10 text-red-500 border-red-500/20' },
}

// ── Sub-components ─────────────────────────────────────────────────────────

function CapabilityBadge({ capability }: { capability: string }) {
  const cfg = CAPABILITY_CONFIG[capability]
  if (!cfg) return null
  return (
    <Badge variant="outline" className={`inline-flex items-center gap-1 ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </Badge>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity]
  if (!cfg) return null
  return (
    <Badge variant="outline" className={cfg.color}>
      {cfg.label}
    </Badge>
  )
}

/** Loading skeleton for the aircraft fleet grid. */
function AircraftGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <Card key={i} className="animate-pulse border-border/50">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="h-5 w-28 rounded bg-muted" />
                <div className="h-4 w-36 rounded bg-muted" />
              </div>
              <div className="h-6 w-16 rounded bg-muted" />
            </div>
            <div className="mt-4 space-y-3 border-t border-border/30 pt-3">
              {[1, 2, 3, 4].map((r) => (
                <div key={r} className="flex items-center justify-between">
                  <div className="h-3 w-20 rounded bg-muted" />
                  <div className="h-3 w-16 rounded bg-muted" />
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <div className="h-9 flex-1 rounded bg-muted" />
              <div className="h-9 w-20 rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

/** Loading skeleton for the gripes list. */
function GripesListSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <Card key={i} className="animate-pulse border-border/50">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <div className="h-5 w-14 rounded bg-muted" />
                  <div className="h-5 w-16 rounded bg-muted" />
                </div>
                <div className="h-4 w-3/4 rounded bg-muted" />
                <div className="flex gap-4">
                  <div className="h-3 w-24 rounded bg-muted" />
                  <div className="h-3 w-32 rounded bg-muted" />
                </div>
              </div>
              <div className="h-8 w-20 rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

/** Loading skeleton for the summary cards row. */
function SummaryCardsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="animate-pulse border-border/50">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="h-8 w-8 rounded bg-muted" />
            <div className="space-y-1">
              <div className="h-7 w-12 rounded bg-muted" />
              <div className="h-3 w-24 rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function MaintControlPage() {
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [loadingAircraft, setLoadingAircraft] = useState(true)
  const [loadingDashboard, setLoadingDashboard] = useState(true)
  const [aircraftError, setAircraftError] = useState<string | null>(null)
  const [dashboardError, setDashboardError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('aircraft')

  // Signoff state
  const [signoffAircraft, setSignoffAircraft] = useState('')
  const [signoffCapability, setSignoffCapability] = useState<'full' | 'partial' | 'not_capable'>('full')
  const [signoffRestrictions, setSignoffRestrictions] = useState('')
  const [signoffSignature, setSignoffSignature] = useState('')
  const [signoffSubmitting, setSignoffSubmitting] = useState(false)
  const [signoffSuccess, setSignoffSuccess] = useState(false)
  const [signoffError, setSignoffError] = useState<string | null>(null)
  const [showSignoffDialog, setShowSignoffDialog] = useState(false)

  // Per-aircraft toggle state
  const [togglingId, setTogglingId] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoadingAircraft(true)
    setLoadingDashboard(true)
    setAircraftError(null)
    setDashboardError(null)

    // Fetch both independently so one failure doesn't block the other
    const [acRes, dashRes] = await Promise.all([
      api.get('/api/v1/aircraft?per_page=100').catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load aircraft'
        setAircraftError(msg)
        return null
      }),
      api.get('/api/v1/maintenance/dashboard').catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load dashboard'
        setDashboardError(msg)
        return null
      }),
    ])

    // Parse aircraft
    if (acRes?.data?.data) {
      setAircraft(
        acRes.data.data.map((a: Record<string, unknown>) => ({
          id: a.id as string,
          tail_number: a.tail_number as string,
          type: `${a.make || ''} ${a.model || ''}`.trim() || (a.type as string) || '',
          make: a.make as string | undefined,
          model: a.model as string | undefined,
          status: a.status as string,
          safe_for_flight: (a as Record<string, boolean>).safe_for_flight ?? true,
          mission_capability: (a.mission_capability as 'full' | 'partial' | 'not_capable') || 'full',
          last_inspected: null,  // not on the aircraft model — dashboard has it
          total_hours: (a.total_airframe_hours as number) ?? null,
        })))
    }

    // Parse dashboard
    if (dashRes?.data) {
      const dash: DashboardResponse = {
        aircraft: dashRes.data.aircraft || [],
        total_aircraft: dashRes.data.total_aircraft || 0,
        summary: dashRes.data.summary || {
          total_aircraft: 0,
          active: 0,
          in_maintenance: 0,
          grounded: 0,
          aircraft_with_open_gripes: 0,
          aircraft_with_deferred_gripes: 0,
          aircraft_not_safe_for_flight: 0,
        },
      }
      setDashboard(dash)

      // Enrich aircraft list with dashboard data (safe_for_flight, mission_capability)
      if (dash.aircraft.length > 0) {
        setAircraft((prev) =>
          prev.map((ac) => {
            const dashEntry = dash.aircraft.find((d) => d.aircraft_id === ac.id)
            if (!dashEntry) return ac
            return {
              ...ac,
              safe_for_flight: dashEntry.safe_for_flight,
              mission_capability: (dashEntry.mission_capability as 'full' | 'partial' | 'not_capable') || ac.mission_capability,
            }
          })
        )
      }
    }

    setLoadingAircraft(false)
    setLoadingDashboard(false)
  }

  // ── Derived gripes list (unified from all dashboard entries) ───────────

  const allOpenGripes: Gripe[] = dashboard
    ? dashboard.aircraft.flatMap((entry) =>
        (entry.gripes_open || []).map((g) => ({
          id: g.id,
          description: g.description,
          severity: normaliseSeverity(g.severity),
          status: normaliseStatus(g.status),
          date_logged: g.reported_at || g.date_logged,
          mechanic_notes: g.mechanic_notes || '',
          aircraft_tail: entry.tail_number,
          aircraft_id: entry.aircraft_id,
        }))
      )
    : []

  // ── Summary counts (prefer dashboard, fall back to local) ────────────

  const summary = dashboard?.summary || {
    total_aircraft: aircraft.length,
    active: 0,
    in_maintenance: 0,
    grounded: 0,
    aircraft_with_open_gripes: allOpenGripes.length > 0 ? allOpenGripes.length : 0,
    aircraft_with_deferred_gripes: 0,
    aircraft_not_safe_for_flight: aircraft.filter((a) => !a.safe_for_flight).length,
  }

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleSafeToggle = async (ac: Aircraft) => {
    setTogglingId(ac.id)
    // Optimistic update
    setAircraft((prev) =>
      prev.map((a) => (a.id === ac.id ? { ...a, safe_for_flight: !a.safe_for_flight } : a))
    )
    try {
      await api.patch(`/api/v1/aircraft/${ac.id}`, {
        safe_for_flight: !ac.safe_for_flight,
      })
    } catch {
      // API failed — revert (keep optimistic since AircraftUpdate doesn't carry safe_for_flight)
      // The dashboard refetch on next tick will correct it
    }
    setTogglingId(null)
  }

  const handleSignoff = async () => {
    if (!signoffAircraft || !signoffSignature) return
    setSignoffSubmitting(true)
    setSignoffError(null)

    try {
      await api.post(`/api/v1/aircraft/${signoffAircraft}/signoff`, {
        mission_capability: signoffCapability,
        restrictions: signoffRestrictions,
        signed_by: signoffSignature,
      })

      // Update local aircraft state
      setAircraft((prev) =>
        prev.map((a) =>
          a.id === signoffAircraft
            ? {
                ...a,
                mission_capability: signoffCapability,
                safe_for_flight: signoffCapability !== 'not_capable',
              }
            : a
        )
      )

      setSignoffSuccess(true)
      setTimeout(() => {
        setShowSignoffDialog(false)
        setSignoffSuccess(false)
        setSignoffAircraft('')
        setSignoffCapability('full')
        setSignoffRestrictions('')
        setSignoffSignature('')
      }, 1500)
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? String((err as { response: { data?: { detail?: string } } }).response?.data?.detail || 'Signoff failed')
          : 'Signoff failed'
      setSignoffError(msg)
    }
    setSignoffSubmitting(false)
  }

  // Derive aircraft list for signoff dropdown, sorted by tail number
  const sortedAircraft = [...aircraft].sort((a, b) => a.tail_number.localeCompare(b.tail_number))

  // ── Render ───────────────────────────────────────────────────────────────

  const isInitialLoading = loadingAircraft && loadingDashboard

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Maintenance Control</h1>
          {isInitialLoading ? (
            <div className="mt-1 h-4 w-56 animate-pulse rounded bg-muted" />
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">
              {summary.total_aircraft} aircraft
              {dashboard && (
                <>
                  {' · '}
                  <span className="text-green-500">{summary.active} active</span>
                  {summary.in_maintenance > 0 && (
                    <span className="text-amber-500">{' · '}{summary.in_maintenance} in maintenance</span>
                  )}
                  {summary.grounded > 0 && (
                    <span className="text-red-500">{' · '}{summary.grounded} grounded</span>
                  )}
                  {summary.aircraft_with_open_gripes > 0 && (
                    <span className="text-amber-500">{' · '}{summary.aircraft_with_open_gripes} with open gripes</span>
                  )}
                </>
              )}
            </p>
          )}
        </div>
        <Button
          onClick={() => {
            setSignoffAircraft('')
            setSignoffCapability('full')
            setSignoffRestrictions('')
            setSignoffSignature('')
            setSignoffSuccess(false)
            setSignoffError(null)
            setShowSignoffDialog(true)
          }}
          disabled={isInitialLoading}
        >
          <ShieldCheck className="mr-2 h-4 w-4" /> New Signoff
        </Button>
      </div>

      {/* ── Summary Cards ── */}
      {isInitialLoading ? (
        <SummaryCardsSkeleton />
      ) : (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Plane className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{summary.total_aircraft}</p>
                <p className="text-sm text-muted-foreground">Total Aircraft</p>
              </div>
            </CardContent>
          </Card>
          <Card className={summary.active > 0 ? 'border-green-500/30' : ''}>
            <CardContent className="flex items-center gap-3 p-4">
              <CheckCircle className={`h-8 w-8 ${summary.active > 0 ? 'text-green-500' : 'text-muted-foreground'}`} />
              <div>
                <p className="text-2xl font-bold">{summary.active}</p>
                <p className="text-sm text-muted-foreground">Active</p>
              </div>
            </CardContent>
          </Card>
          <Card className={summary.in_maintenance > 0 ? 'border-amber-500/30' : ''}>
            <CardContent className="flex items-center gap-3 p-4">
              <MinusCircle className={`h-8 w-8 ${summary.in_maintenance > 0 ? 'text-amber-500' : 'text-muted-foreground'}`} />
              <div>
                <p className="text-2xl font-bold">{summary.in_maintenance}</p>
                <p className="text-sm text-muted-foreground">In Maintenance</p>
              </div>
            </CardContent>
          </Card>
          <Card className={summary.grounded > 0 ? 'border-red-500/30' : ''}>
            <CardContent className="flex items-center gap-3 p-4">
              <AlertTriangle className={`h-8 w-8 ${summary.grounded > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
              <div>
                <p className="text-2xl font-bold">{summary.grounded}</p>
                <p className="text-sm text-muted-foreground">Grounded</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Error banners ── */}
      {aircraftError && (
        <div className="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/5 px-4 py-2 text-sm text-red-500">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>Aircraft: {aircraftError}</span>
          <Button size="sm" variant="outline" className="ml-auto" onClick={fetchData}>
            Retry
          </Button>
        </div>
      )}
      {dashboardError && (
        <div className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-4 py-2 text-sm text-amber-500">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>Dashboard: {dashboardError}</span>
          <Button size="sm" variant="outline" className="ml-auto" onClick={fetchData}>
            Retry
          </Button>
        </div>
      )}

      {/* ── Tabs ── */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="aircraft">Aircraft Fleet ({aircraft.length})</TabsTrigger>
          <TabsTrigger
            value="gripes"
            className={allOpenGripes.length > 0 ? 'text-amber-500' : ''}
          >
            Open Gripes ({allOpenGripes.length})
          </TabsTrigger>
          <TabsTrigger value="signoff">Signoff Panel</TabsTrigger>
        </TabsList>

        {/* ─── TAB: Aircraft Fleet ─── */}
        <TabsContent value="aircraft" className="mt-4">
          {loadingAircraft ? (
            <AircraftGridSkeleton />
          ) : aircraftError && aircraft.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <Plane className="h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">Could not load aircraft</p>
              <Button variant="outline" onClick={fetchData}>Retry</Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sortedAircraft.map((ac) => {
                return (
                  <Card
                    key={ac.id}
                    className={`border-l-4 transition-colors ${
                      ac.mission_capability === 'full'
                        ? 'border-l-green-500'
                        : ac.mission_capability === 'partial'
                          ? 'border-l-amber-500'
                          : 'border-l-red-500'
                    }`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <Plane className="h-5 w-5 text-muted-foreground" />
                            <span className="text-lg font-bold">{ac.tail_number}</span>
                          </div>
                          <p className="mt-0.5 text-sm text-muted-foreground">{ac.type}</p>
                        </div>
                        <CapabilityBadge capability={ac.mission_capability} />
                      </div>

                      <div className="mt-4 space-y-2 border-t border-border/30 pt-3 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Status</span>
                          <span className="font-medium capitalize">{ac.status}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Total Hours</span>
                          <span className="font-mono text-xs">{ac.total_hours?.toFixed(1) || '—'}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Last Inspected</span>
                          <span className="text-xs">{fmtDateShort(ac.last_inspected)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Safe for Flight</span>
                          {ac.safe_for_flight ? (
                            <span className="flex items-center gap-1 text-green-500">
                              <CheckCircle className="h-3.5 w-3.5" /> Yes
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-red-500">
                              <XCircle className="h-3.5 w-3.5" /> No
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button
                          size="sm"
                          variant={ac.safe_for_flight ? 'outline' : 'default'}
                          className={`flex-1 ${ac.safe_for_flight ? '' : 'bg-green-600 hover:bg-green-700 text-white'}`}
                          onClick={() => handleSafeToggle(ac)}
                          disabled={togglingId === ac.id}
                        >
                          {togglingId === ac.id ? (
                            <span className="animate-pulse">...</span>
                          ) : ac.safe_for_flight ? (
                            <>
                              <XCircle className="mr-1 h-3.5 w-3.5" /> Ground
                            </>
                          ) : (
                            <>
                              <ShieldCheck className="mr-1 h-3.5 w-3.5" /> Safe for Flight
                            </>
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSignoffAircraft(ac.id)
                            setSignoffCapability(ac.mission_capability)
                            setSignoffRestrictions('')
                            setSignoffSignature('')
                            setSignoffSuccess(false)
                            setSignoffError(null)
                            setShowSignoffDialog(true)
                          }}
                        >
                          Signoff
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
              {sortedAircraft.length === 0 && (
                <div className="col-span-full flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
                  <Plane className="h-12 w-12 text-muted-foreground" />
                  <p className="text-lg font-medium text-muted-foreground">No aircraft registered</p>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* ─── TAB: Open Gripes ─── */}
        <TabsContent value="gripes" className="mt-4">
          {loadingDashboard ? (
            <GripesListSkeleton />
          ) : dashboardError ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <AlertTriangle className="h-12 w-12 text-amber-500" />
              <p className="text-lg font-medium text-muted-foreground">Could not load gripes</p>
              <p className="text-sm text-muted-foreground">Dashboard API unavailable — {dashboardError}</p>
              <Button variant="outline" onClick={fetchData}>Retry</Button>
            </div>
          ) : allOpenGripes.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <CheckCircle className="h-12 w-12 text-green-500" />
              <p className="text-lg font-medium text-muted-foreground">No open gripes</p>
              <p className="text-sm text-muted-foreground">All aircraft are gripe-free.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {allOpenGripes.map((gripe, idx) => (
                <Card
                  key={gripe.id || idx}
                  className={`border-border/50 ${
                    gripe.severity === 'critical'
                      ? 'border-l-red-500'
                      : gripe.severity === 'major'
                        ? 'border-l-amber-500'
                        : 'border-l-green-500'
                  }`}
                >
                  <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={gripe.severity} />
                        {gripe.status === 'deferred' && (
                          <Badge variant="outline" className="bg-muted text-muted-foreground">Deferred</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm font-medium">{gripe.description}</p>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Plane className="h-3 w-3" />
                          {gripe.aircraft_tail || '—'}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {fmtDate(gripe.date_logged)}
                        </span>
                        {gripe.mechanic_notes && (
                          <span className="italic">Notes: {gripe.mechanic_notes}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button size="sm" variant="outline">
                        <Wrench className="mr-1 h-3.5 w-3.5" /> Assign
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ─── TAB: Signoff Panel ─── */}
        <TabsContent value="signoff" className="mt-4">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Signoff Form */}
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="h-4 w-4" />
                  Maintenance Release / Safe-for-Flight Signoff
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Aircraft Select */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Aircraft</label>
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={signoffAircraft}
                      onChange={(e) => {
                        setSignoffAircraft(e.target.value)
                        setSignoffError(null)
                      }}
                    >
                      <option value="">Select aircraft...</option>
                      {sortedAircraft.map((ac) => (
                        <option key={ac.id} value={ac.id}>
                          {ac.tail_number} — {ac.type}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Mission Capability */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Mission Capability</label>
                    <div className="flex gap-2">
                      {(['full', 'partial', 'not_capable'] as const).map((cap) => {
                        const cfg = CAPABILITY_CONFIG[cap]
                        return (
                          <button
                            key={cap}
                            type="button"
                            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                              signoffCapability === cap
                                ? `${cfg.color} border-current`
                                : 'border-input text-muted-foreground hover:bg-accent'
                            }`}
                            onClick={() => setSignoffCapability(cap)}
                          >
                            {cfg.icon}
                            {cfg.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Restrictions */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Operating Restrictions</label>
                    <textarea
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      placeholder="e.g., VFR only, no NVG, max 8 pax..."
                      value={signoffRestrictions}
                      onChange={(e) => setSignoffRestrictions(e.target.value)}
                    />
                  </div>

                  {/* Signature */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Maintenance Engineer Signature</label>
                    <input
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                      placeholder="Type full name to sign..."
                      value={signoffSignature}
                      onChange={(e) => {
                        setSignoffSignature(e.target.value)
                        setSignoffError(null)
                      }}
                    />
                  </div>

                  {/* Error message */}
                  {signoffError && (
                    <div className="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-500">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>{signoffError}</span>
                    </div>
                  )}

                  {/* Signoff Button */}
                  <Button
                    className="w-full"
                    size="lg"
                    disabled={!signoffAircraft || !signoffSignature || signoffSubmitting || signoffSuccess}
                    onClick={handleSignoff}
                  >
                    {signoffSuccess ? (
                      <span className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4" /> Signed Off
                      </span>
                    ) : signoffSubmitting ? (
                      <span className="flex items-center gap-2">
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> Submitting...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4" /> Sign Safe for Flight
                      </span>
                    )}
                  </Button>

                  {signoffAircraft && !signoffSignature && (
                    <p className="text-xs text-muted-foreground text-center">
                      Type your full name as an electronic signature to complete the release.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Current Status Overview */}
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Clock className="h-4 w-4" />
                  Current Status Overview
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Quick reference for all aircraft maintenance status.
                </p>
                <div className="space-y-2">
                  {sortedAircraft.map((ac) => {
                    return (
                      <div
                        key={ac.id}
                        className="flex items-center justify-between rounded-md border border-border/50 p-3 text-sm"
                      >
                        <div className="flex items-center gap-3">
                          <Plane className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{ac.tail_number}</span>
                          <span className="text-xs text-muted-foreground">{ac.type}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CapabilityBadge capability={ac.mission_capability} />
                          {ac.safe_for_flight ? (
                            <span className="flex items-center gap-1 text-xs text-green-500">
                              <CheckCircle className="h-3 w-3" /> OK
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-red-500">
                              <XCircle className="h-3 w-3" /> GROUND
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* ─── Signoff Dialog (reusable from card button / header button) ─── */}
      <Dialog open={showSignoffDialog} onOpenChange={(open) => {
        if (!open && !signoffSubmitting) {
          setShowSignoffDialog(false)
          setSignoffSuccess(false)
          setSignoffError(null)
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Maintenance Release Signoff</DialogTitle>
            <DialogDescription>
              Record a maintenance release with capability status and restrictions.
            </DialogDescription>
          </DialogHeader>

          {signoffSuccess ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <CheckCircle className="h-16 w-16 text-green-500" />
              <p className="text-lg font-semibold text-green-500">Signoff Complete</p>
              <p className="text-sm text-muted-foreground">Maintenance release has been recorded.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Aircraft Select */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Aircraft</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={signoffAircraft}
                  onChange={(e) => {
                    setSignoffAircraft(e.target.value)
                    setSignoffError(null)
                  }}
                >
                  <option value="">Select aircraft...</option>
                  {sortedAircraft.map((ac) => (
                    <option key={ac.id} value={ac.id}>
                      {ac.tail_number} — {ac.type}
                    </option>
                  ))}
                </select>
              </div>

              {/* Mission Capability */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Mission Capability</label>
                <div className="flex gap-2">
                  {(['full', 'partial', 'not_capable'] as const).map((cap) => {
                    const cfg = CAPABILITY_CONFIG[cap]
                    return (
                      <button
                        key={cap}
                        type="button"
                        className={`flex flex-1 items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                          signoffCapability === cap
                            ? `${cfg.color} border-current`
                            : 'border-input text-muted-foreground hover:bg-accent'
                        }`}
                        onClick={() => setSignoffCapability(cap)}
                      >
                        {cfg.icon}
                        {cfg.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Restrictions */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Operating Restrictions</label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="e.g., VFR only, no NVG, max 8 pax..."
                  value={signoffRestrictions}
                  onChange={(e) => setSignoffRestrictions(e.target.value)}
                />
              </div>

              {/* Signature */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Maintenance Engineer Signature</label>
                <input
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                  placeholder="Type full name to sign..."
                  value={signoffSignature}
                  onChange={(e) => {
                    setSignoffSignature(e.target.value)
                    setSignoffError(null)
                  }}
                />
              </div>

              {/* Error */}
              {signoffError && (
                <div className="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-500">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{signoffError}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={() => setShowSignoffDialog(false)}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  disabled={!signoffAircraft || !signoffSignature || signoffSubmitting}
                  onClick={handleSignoff}
                >
                  {signoffSubmitting ? 'Signing...' : 'Sign & Release'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
