import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plane, MapPin, Users, Fuel, FileWarning, Map, CheckCircle, Trash2, Scale, Clock, RefreshCw, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'
import RouteMap from '@/features/map/RouteMap'
import type { RouteLeg } from '@/features/map/RouteMap'
import { SectionErrorBoundary } from '@/components/ui/error-boundary'
import { useAuthContext } from '@/features/auth/AuthContext'
import type { RoutePlanResponse, CrewMemberDuty } from '@/types'
import CostsPnlSection from '@/features/costs/CostsPnlSection'

// ── W&B Status Badge ──────────────────────────────────────────────────────
function WBStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ok: 'bg-green-500/10 text-green-500 border-green-500/20',
    warning: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    over_limit: 'bg-red-500/10 text-red-500 border-red-500/20',
  }
  return <Badge variant="outline" className={colors[status] || ''}>{status.replace('_', ' ')}</Badge>
}

export default function MissionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthContext()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [routePlan, setRoutePlan] = useState<RoutePlanResponse | null>(null)
  const [wbLoading, setWbLoading] = useState(false)
  const [dutyLoading, setDutyLoading] = useState(false)
  const [wbError, setWbError] = useState('')
  const [dutyError, setDutyError] = useState('')

  const callRoutePlanner = useCallback(async () => {
    if (!id || !data?.mission?.aircraft_id) return null
    try {
      const legs = (data.mission.legs || []).map((leg: any) => ({
        origin: leg.departure_airport,
        destination: leg.arrival_airport,
      }))
      if (legs.length === 0) return null
      const res = await api.post('/api/v1/routes/plan', {
        aircraft_id: data.mission.aircraft_id,
        legs,
        crew_count: 2,
        is_two_pilot: true,
      })
      return res.data.plan as RoutePlanResponse
    } catch {
      return null
    }
  }, [id, data])

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/missions/${id}`)
      .then((res) => setData(res.data))
      .catch(() => navigate('/missions'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!data) return null

  const { mission, warnings } = data
  const legs = mission.legs || []

  // Known airport coordinates for the Bahamas/Caribbean region
  // (will be replaced by API-driven lookup post-spike)
  const AIRPORT_COORDS: Record<string, { lat: number; lon: number }> = {
    MYNN: { lat: 25.0390, lon: -77.4661 },
    MYGF: { lat: 26.5581, lon: -78.6957 },
    MYIG: { lat: 20.9750, lon: -73.6669 },
    MYEH: { lat: 25.4697, lon: -76.6838 },
    MYPB: { lat: 27.9111, lon: -77.7031 },
    MYBS: { lat: 24.1778, lon: -76.1678 },
    MYSM: { lat: 24.1328, lon: -74.3122 },
    MYAB: { lat: 26.0025, lon: -77.3958 },
    MYCI: { lat: 22.7456, lon: -74.1822 },
    MYER: { lat: 24.8894, lon: -76.1736 },
    MYEM: { lat: 25.2872, lon: -76.3302 },
    MYBC: { lat: 25.7250, lon: -79.2972 },
    MYRD: { lat: 26.3033, lon: -77.4419 },
    MYLS: { lat: 23.6550, lon: -75.3411 },
    MTCW: { lat: 19.7000, lon: -71.8500 },
    MTPP: { lat: 18.5711, lon: -72.2936 },
    MTCH: { lat: 19.7333, lon: -71.6667 },
    MTEG: { lat: 18.2000, lon: -71.1069 },
    MDPP: { lat: 19.7578, lon: -70.5697 },
    MDBH: { lat: 18.2517, lon: -71.1244 },
    MDSD: { lat: 18.4294, lon: -69.6689 },
    KFLL: { lat: 26.0726, lon: -80.1527 },
    KMIA: { lat: 25.7933, lon: -80.2906 },
    KORD: { lat: 41.9786, lon: -87.9048 },
    KJFK: { lat: 40.6413, lon: -73.7781 },
  }

  function getCoords(icao: string): { lat: number; lon: number } {
    return AIRPORT_COORDS[icao.toUpperCase()] ?? { lat: 25.0, lon: -77.0 }
  }

  const routeLegs: RouteLeg[] = legs.map((leg: any, i: number) => {
    const dep = leg.departure_airport?.toUpperCase() || ''
    const arr = leg.arrival_airport?.toUpperCase() || ''
    const depCoords = getCoords(dep)
    const arrCoords = getCoords(arr)
    return {
      leg: leg.leg_number || i + 1,
      origin: dep,
      destination: arr,
      origin_lat: depCoords.lat,
      origin_lon: depCoords.lon,
      dest_lat: arrCoords.lat,
      dest_lon: arrCoords.lon,
      origin_name: dep,
      destination_name: arr,
      distance_nm: leg.distance_nm || 0,
    }
  })

  const isSuperAdmin = user?.role === 'super_admin'

  const handleDelete = async () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    setDeleteLoading(true)
    try {
      await api.delete(`/api/v1/missions/${mission.id}`)
      navigate('/missions')
    } catch {
      setConfirmDelete(false)
      setDeleteLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/missions')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Mission</h1>
            <Badge className={
              mission.status === 'active' ? 'bg-green-500' :
              mission.status === 'completed' ? 'bg-blue-500' : ''
            }>{mission.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {legs.length > 0 && `${legs.map((l: any) => l.departure_airport).join(' → ')} → ${legs[legs.length-1].arrival_airport} · `}
            {mission.home_base} base
          </p>
        </div>
      </div>

      {/* Warnings */}
      {warnings?.length > 0 && (
        <div className="space-y-2">
          {warnings.map((w: string, i: number) => (
            <div key={i} className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-500">
              <FileWarning className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Route Overview Map */}
      {routeLegs.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Map className="h-4 w-4 text-brand-400" />
              Route Overview
            </CardTitle>
            <Badge variant="outline" className="bg-brand-500/10 text-brand-500 border-brand-500/20">
              {routeLegs.length} {routeLegs.length === 1 ? 'leg' : 'legs'}
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            <SectionErrorBoundary>
              <RouteMap legs={routeLegs} />
            </SectionErrorBoundary>
          </CardContent>
        </Card>
      )}

      {/* Leg Timeline */}
      <Card>
        <CardHeader><CardTitle className="text-base flex items-center gap-2"><MapPin className="h-4 w-4" /> Route</CardTitle></CardHeader>
        <CardContent>
          <div className="relative space-y-0">
            {legs.map((leg: any, i: number) => (
              <div key={leg.id} className="flex gap-4 pb-6 last:pb-0">
                {/* Timeline line */}
                <div className="flex flex-col items-center">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                    leg.status === 'completed' ? 'bg-green-500 text-white' :
                    leg.status === 'active' ? 'bg-amber-500 text-white' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {leg.leg_number}
                  </div>
                  {i < legs.length - 1 && <div className="mt-1 h-full w-0.5 bg-border" />}
                </div>
                {/* Leg content */}
                <div className="flex-1 rounded-lg border border-border/50 p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{leg.departure_airport} → {leg.arrival_airport}</p>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                        {leg.distance_nm && <span>{leg.distance_nm} nm</span>}
                        {leg.fuel_required_l && <span className="flex items-center gap-1"><Fuel className="h-3 w-3" />{leg.fuel_required_l}L req</span>}
                        {leg.fuel_on_board_l && <span>{leg.fuel_on_board_l}L onboard</span>}
                      </div>
                    </div>
                    <Badge variant="outline" className={
                      leg.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                      leg.status === 'active' ? 'bg-amber-500/10 text-amber-500' : ''
                    }>{leg.status}</Badge>
                  </div>
                  {leg.notams && (
                    <div className="mt-2 rounded bg-amber-500/5 px-2 py-1 text-xs text-amber-500">
                      NOTAM: {leg.notams}
                    </div>
                  )}
                  {/* Manifest summary */}
                  {leg.manifest_entries?.length > 0 && (
                    <div className="mt-2 border-t border-border/50 pt-2">
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Users className="h-3 w-3" />
                        {leg.manifest_entries.filter((e: any) => e.entry_type === 'passenger').length} passengers
                        {leg.manifest_entries.filter((e: any) => e.entry_type === 'cargo').length > 0 &&
                          ` · ${leg.manifest_entries.filter((e: any) => e.entry_type === 'cargo').length} cargo`
                        }
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Weight & Balance */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Scale className="h-4 w-4 text-brand-400" />
            Weight & Balance
          </CardTitle>
          <div className="flex items-center gap-2">
            {wbError && <span className="text-xs text-red-500">{wbError}</span>}
            <Button
              variant="outline"
              size="sm"
              disabled={wbLoading || !data?.mission?.aircraft_id}
              onClick={async () => {
                setWbLoading(true)
                setWbError('')
                const plan = await callRoutePlanner()
                if (plan) {
                  setRoutePlan(plan)
                } else {
                  setWbError('Route planner unavailable — check aircraft assignment')
                }
                setWbLoading(false)
              }}
            >
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${wbLoading ? 'animate-spin' : ''}`} />
              {wbLoading ? 'Loading...' : 'Refresh W&B'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!routePlan ? (
            <p className="text-sm text-muted-foreground italic">
              {data?.mission?.aircraft_id
                ? 'Click "Refresh W&B" to load weight & balance data.'
                : 'Assign an aircraft to this mission to enable W&B calculations.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Leg</th>
                    <th className="py-2 pr-3 font-medium">Route</th>
                    <th className="py-2 pr-3 font-medium">TOW</th>
                    <th className="py-2 pr-3 font-medium">MTOW</th>
                    <th className="py-2 pr-3 font-medium">Mgn</th>
                    <th className="py-2 pr-3 font-medium">MTOW</th>
                    <th className="py-2 pr-3 font-medium">MLW</th>
                    <th className="py-2 pr-3 font-medium">ZFW</th>
                    <th className="py-2 pr-3 font-medium">Cargo</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {routePlan.legs.filter(l => l.weight_balance).map((leg) => {
                    const wb = leg.weight_balance!
                    const statusColor = wb.overall_status === 'over_limit' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                      wb.overall_status === 'warning' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                      'bg-green-500/10 text-green-500 border-green-500/20'
                    return (
                      <tr key={leg.leg} className="border-b border-border/20">
                        <td className="py-2 pr-3 font-mono text-xs">{leg.leg}</td>
                        <td className="py-2 pr-3 font-medium">{leg.origin}→{leg.destination}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{Math.round(wb.weights.takeoff_kg).toLocaleString()}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{Math.round(wb.limits.mtow_kg).toLocaleString()}</td>
                        <td className="py-2 pr-3 font-mono text-xs">
                          <span className={wb.margins.mtow_margin_kg < 0 ? 'text-red-500' : wb.margins.mtow_margin_kg < 50 ? 'text-amber-500' : ''}>
                            {Math.round(wb.margins.mtow_margin_kg).toLocaleString()}
                          </span>
                        </td>
                        <td className="py-2 pr-3">
                          <WBStatusBadge status={wb.margins.mtow_status} />
                        </td>
                        <td className="py-2 pr-3">
                          <WBStatusBadge status={wb.margins.mlw_status} />
                        </td>
                        <td className="py-2 pr-3">
                          <WBStatusBadge status={wb.margins.zfw_status} />
                        </td>
                        <td className="py-2 pr-3">
                          <WBStatusBadge status={wb.margins.cargo_status} />
                        </td>
                        <td className="py-2">
                          <Badge variant="outline" className={statusColor}>{wb.overall_status.replace('_', ' ')}</Badge>
                        </td>
                      </tr>
                    )
                  })}
                  {routePlan.legs.filter(l => l.weight_balance).length === 0 && (
                    <tr><td colSpan={10} className="py-4 text-center text-sm text-muted-foreground">No W&B data available for these legs.</td></tr>
                  )}
                </tbody>
              </table>
              {/* W&B notes/warnings */}
              {routePlan.legs.some(l => l.weight_balance?.notes?.length) && (
                <div className="mt-3 space-y-1">
                  {routePlan.legs.map((leg) =>
                    leg.weight_balance?.notes?.map((note, ni) => (
                      <div key={`${leg.leg}-${ni}`} className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-2 text-xs text-amber-500">
                        <FileWarning className="mt-0.5 h-3 w-3 shrink-0" />
                        <span>Leg {leg.leg}: {note}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Crew Duty */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4 text-brand-400" />
            Crew Duty
          </CardTitle>
          <div className="flex items-center gap-2">
            {dutyError && <span className="text-xs text-red-500">{dutyError}</span>}
            <Button
              variant="outline"
              size="sm"
              disabled={dutyLoading || !data?.mission?.aircraft_id}
              onClick={async () => {
                setDutyLoading(true)
                setDutyError('')
                const plan = await callRoutePlanner()
                if (plan) {
                  setRoutePlan(plan)
                } else {
                  setDutyError('Route planner unavailable — check aircraft assignment')
                }
                setDutyLoading(false)
              }}
            >
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${dutyLoading ? 'animate-spin' : ''}`} />
              {dutyLoading ? 'Loading...' : 'Refresh Duty'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!routePlan?.crew_duty ? (
            <p className="text-sm text-muted-foreground italic">
              {data?.mission?.aircraft_id
                ? 'Click "Refresh Duty" to load crew duty data.'
                : 'Assign an aircraft to this mission to enable crew duty calculations.'}
            </p>
          ) : (
            <div className="space-y-3">
              {/* Mission-level legal badge */}
              <div className="flex items-center gap-3">
                <Badge variant="outline" className={
                  routePlan.crew_duty.mission_legal
                    ? 'bg-green-500/10 text-green-500 border-green-500/20'
                    : 'bg-red-500/10 text-red-500 border-red-500/20'
                }>
                  {routePlan.crew_duty.mission_legal ? 'PASS — Legal' : 'FAIL — Violation'}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {routePlan.crew_duty.is_two_pilot ? '2-pilot' : '1-pilot'} crew · {routePlan.crew_duty.flight_time_limit_24hr}hr flight limit
                </span>
              </div>

              {/* Per-crew table */}
              {routePlan.crew_duty.crew.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground">
                        <th className="py-2 pr-3 font-medium">Name</th>
                        <th className="py-2 pr-3 font-medium">Role</th>
                        <th className="py-2 pr-3 font-medium">Flight Time</th>
                        <th className="py-2 pr-3 font-medium">Duty Period</th>
                        <th className="py-2 pr-3 font-medium">24hr Flight</th>
                        <th className="py-2 pr-3 font-medium">Rest</th>
                        <th className="py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {routePlan.crew_duty.crew.map((member: CrewMemberDuty, i: number) => (
                        <tr key={i} className="border-b border-border/20">
                          <td className="py-2 pr-3 font-medium">{member.name}</td>
                          <td className="py-2 pr-3 text-muted-foreground">{member.role.replace('_', ' ')}</td>
                          <td className="py-2 pr-3 font-mono text-xs">{member.duty.flight_time_hours.toFixed(1)}h</td>
                          <td className="py-2 pr-3 font-mono text-xs">{member.duty.duty_period_hours.toFixed(1)}h</td>
                          <td className="py-2 pr-3 font-mono text-xs">{member.duty.flight_time_24hr.toFixed(1)}h</td>
                          <td className="py-2 pr-3">
                            <span className={member.rest.rest_adequate ? 'text-green-500' : 'text-red-500'}>
                              {member.rest.rest_hours_received.toFixed(1)}h
                            </span>
                          </td>
                          <td className="py-2">
                            <Badge variant="outline" className={
                              member.is_legal
                                ? 'bg-green-500/10 text-green-500 border-green-500/20'
                                : 'bg-red-500/10 text-red-500 border-red-500/20'
                            }>
                              {member.is_legal ? 'PASS' : 'FAIL'}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Violations */}
              {routePlan.crew_duty.mission_violations.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-red-500">Violations</p>
                  {routePlan.crew_duty.mission_violations.map((v: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 p-2 text-xs text-red-500">
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      <span>{v}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Warnings */}
              {routePlan.crew_duty.crew.some(m => m.warnings.length > 0) && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-amber-500">Crew Warnings</p>
                  {routePlan.crew_duty.crew.map((member: CrewMemberDuty, mi: number) =>
                    member.warnings.map((w: string, wi: number) => (
                      <div key={`${mi}-${wi}`} className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-2 text-xs text-amber-500">
                        <FileWarning className="mt-0.5 h-3 w-3 shrink-0" />
                        <span>{member.name}: {w}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Costs & P&L */}
      <CostsPnlSection
        missionId={id!}
        legs={legs.map((leg: any) => ({
          leg_number: leg.leg_number,
          departure_airport: leg.departure_airport,
          arrival_airport: leg.arrival_airport,
        }))}
      />

      {/* Actions */}
      <div className="flex gap-3">
        {isSuperAdmin && (
          <>
            {mission.status === 'draft' && (
              <Button onClick={async () => {
                await api.patch(`/api/v1/missions/${mission.id}`, { status: 'active' })
                window.location.reload()
              }}>
                <Plane className="mr-2 h-4 w-4" /> Activate Mission
              </Button>
            )}
            {mission.status === 'active' && (
              <Button onClick={async () => {
                await api.patch(`/api/v1/missions/${mission.id}`, { status: 'completed' })
                window.location.reload()
              }}>
                <CheckCircle className="mr-2 h-4 w-4" /> Complete Mission
              </Button>
            )}
            <Button variant="destructive" onClick={handleDelete} disabled={deleteLoading}>
              <Trash2 className="mr-2 h-4 w-4" />
              {confirmDelete ? 'Confirm Delete?' : 'Delete'}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
