import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, X, ArrowLeft, Plane, Users, Search, FileWarning, Clock, Route, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'
import { Acronym, AcronymSpan } from '@/components/ui/acronym'

interface Aircraft { id: string; tail_number: string; make?: string; model?: string }
interface CrewMember { id: string; display_name: string; role: string; qualifications?: { aircraft_type?: string }[] }
interface LegForm { leg_number: number; departure: string; arrival: string }
interface PaxForm { name: string; nationality: string; weight: string }
interface RoutePlan { aircraft: any; legs: any[]; totals: any; crew_duty: any; flags: any }

export default function MissionBuilderPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [acId, setAcId] = useState('')
  const [picId, setPicId] = useState('')
  const [sicId, setSicId] = useState('')
  const [isTwoPilot, setIsTwoPilot] = useState(true)
  const [homeBase] = useState('MYNN')
  const [legs, setLegs] = useState<LegForm[]>([{ leg_number: 1, departure: 'MYNN', arrival: '' }])
  const [passengers, setPassengers] = useState<PaxForm[]>([])
  const [paxSearch, setPaxSearch] = useState('')
  const [paxResults, setPaxResults] = useState<any[]>([])
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [planError, setPlanError] = useState('')
  const [missionId, setMissionId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [createWarnings, setCreateWarnings] = useState<string[]>([])

  useEffect(() => {
    api.get('/api/v1/aircraft?per_page=100').then((r) => setAircraft(r.data.data || []))
    api.get('/api/v1/crew?per_page=100').then((r) => setCrew(r.data.data || []))
  }, [])

  const selectedAircraft = aircraft.find((a) => a.id === acId)

  // Filter crew by aircraft type rating — match qual code against aircraft model
  const acTypeCode = selectedAircraft ? (
    selectedAircraft.model?.includes('BT-67') || selectedAircraft.model?.includes('BT67') ? 'BT67' :
    selectedAircraft.model?.includes('350i') || selectedAircraft.model?.includes('K35X') ? 'K35X' :
    selectedAircraft.model?.includes('200GT') || selectedAircraft.model?.includes('200') && selectedAircraft.model?.includes('King') ? 'K200' :
    selectedAircraft.model?.includes('T300') || selectedAircraft.model?.includes('Caravan') ? 'T300' :
    selectedAircraft.model?.includes('Twin Otter') || selectedAircraft.model?.includes('DHC') ? 'DHC6' : ''
  ) : ''

  const eligibleCrew = crew.filter((c) => {
    if (!acTypeCode) return true
    if (!c.qualifications || c.qualifications.length === 0) return false
    return c.qualifications.some((q) => q.aircraft_type === acTypeCode)
  })

  const updateLeg = (idx: number, field: string, value: string) => {
    const updated = legs.map((leg, i) => {
      if (i !== idx) return leg
      const newLeg = { ...leg, [field]: value.toUpperCase() }
      // Auto-fill next leg departure
      if (field === 'arrival' && i < legs.length - 1) {
        const next = [...legs]
        next[i + 1] = { ...next[i + 1], departure: value.toUpperCase() }
      }
      return newLeg
    })
    setLegs(updated)
  }

  const addLeg = () => {
    const last = legs[legs.length - 1]
    setLegs([...legs, { leg_number: legs.length + 1, departure: last.arrival || '', arrival: '' }])
  }

  const removeLeg = (idx: number) => {
    if (legs.length <= 1) return
    setLegs(legs.filter((_, i) => i !== idx).map((l, i) => ({ ...l, leg_number: i + 1 })))
  }

  const callRoutePlanner = async () => {
    if (!acId) return
    setPlanLoading(true)
    setPlanError('')
    setRoutePlan(null)
    try {
      const reqLegs = legs
        .filter((l) => l.departure && l.arrival)
        .map((l) => ({ origin: l.departure, destination: l.arrival }))
      if (reqLegs.length === 0) { setPlanError('Enter at least one leg'); setPlanLoading(false); return }
      const crewMembers = []
      if (picId) crewMembers.push({ id: picId, role: 'captain' })
      if (sicId) crewMembers.push({ id: sicId, role: isTwoPilot ? 'first_officer' : 'sic' })
      const res = await api.post('/api/v1/routes/plan', {
        aircraft_id: acId,
        legs: reqLegs,
        crew_count: isTwoPilot ? 2 : 1,
        is_two_pilot: isTwoPilot,
        crew_members: crewMembers.length > 0 ? crewMembers : undefined,
      })
      setRoutePlan(res.data.plan)
      setStep(3)
    } catch (err: any) {
      setPlanError(err?.response?.data?.detail || 'Route planning failed. Check ICAO codes.')
    }
    setPlanLoading(false)
  }

  const handleCreate = async () => {
    if (!routePlan) return
    setSubmitting(true)
    try {
      const m = await api.post('/api/v1/missions', {
        aircraft_id: acId || undefined,
        home_base: homeBase,
        pilot_in_command: picId || undefined,
        second_in_command: sicId || undefined,
      })
      const mid = m.data.id
      setMissionId(mid)

      // Create legs from route plan
      for (const leg of routePlan.legs) {
        await api.post(`/api/v1/missions/${mid}/legs`, {
          leg_number: leg.leg,
          departure_airport: leg.origin,
          arrival_airport: leg.destination,
          distance_nm: Math.round(leg.distance_nm) || undefined,
        })
      }

      // Add passengers to first leg
      for (const pax of passengers) {
        await api.post(`/api/v1/missions/${mid}/legs/${routePlan.legs[0]?.leg || 1}/manifest`, {
          full_name: pax.name,
          nationality: pax.nationality,
          weight_kg: pax.weight ? parseFloat(pax.weight) : undefined,
          entry_type: 'passenger',
          boarding_leg_number: 1,
        })
      }

      const detail = await api.get(`/api/v1/missions/${mid}`)
      setCreateWarnings(detail.data.warnings || [])
      setStep(5)
    } catch { /* silent */ }
    setSubmitting(false)
  }

  const addPassenger = () => setPassengers([...passengers, { name: '', nationality: 'US', weight: '80' }])
  const updatePax = (idx: number, field: string, value: string) => {
    setPassengers(passengers.map((p, i) => i === idx ? { ...p, [field]: value } : p))
  }
  const removePax = (idx: number) => setPassengers(passengers.filter((_, i) => i !== idx))

  const totalSteps = 5
  const stepLabel = (s: number) => ['Aircraft & Crew', 'Route Legs', 'Plan Review', 'Passengers', 'Review'][s - 1]

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/missions')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold tracking-tight">New Mission</h1>
            {routePlan && step < 5 && (
              <Badge variant="outline" className="bg-brand-500/10 text-brand-500 border-brand-500/20">
                {Math.round(routePlan.totals?.total_distance_nm || 0)} nm · {routePlan.totals?.total_block_hours || 0}h
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-sm text-muted-foreground">{stepLabel(step)} — Step {step} of {totalSteps}</p>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1">
        {Array.from({ length: totalSteps }, (_, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full ${i + 1 <= step ? 'bg-brand-500' : 'bg-muted'}`} />
        ))}
      </div>

      {/* ── Step 1: Aircraft & Crew ───────────────────────────────────── */}
      {step === 1 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Plane className="h-5 w-5 text-brand-400" /> Aircraft & Crew
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Aircraft</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={acId} onChange={(e) => { setAcId(e.target.value); setPicId(''); setSicId('') }}>
                  <option value="">Select aircraft...</option>
                  {aircraft.map((a) => (
                    <option key={a.id} value={a.id}>{a.tail_number} {a.make ? `(${a.make})` : ''}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Operation</label>
                <div className="flex h-10 items-center gap-3 rounded-md border border-input bg-background px-3">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="crew" checked={isTwoPilot} onChange={() => setIsTwoPilot(true)} />
                    2-pilot
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="crew" checked={!isTwoPilot} onChange={() => setIsTwoPilot(false)} />
                    Single pilot
                  </label>
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">Home base: {homeBase}</p>

            {/* PIC selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Pilot in Command {isTwoPilot ? '(PIC)' : ''}</label>
              {eligibleCrew.length === 0 ? (
                <p className="text-xs text-muted-foreground">No qualified crew in database</p>
              ) : (
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={picId} onChange={(e) => setPicId(e.target.value)}>
                  <option value="">Select PIC...</option>
                  {eligibleCrew.map((c) => (
                    <option key={c.id} value={c.id}>{c.display_name} ({c.role})</option>
                  ))}
                </select>
              )}
            </div>

            {/* SIC selection (2-pilot only) */}
            {isTwoPilot && (
              <div className="space-y-2">
                <label className="text-sm font-medium"><AcronymSpan text="SIC" /> / <AcronymSpan text="FO" /></label>
                {eligibleCrew.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No qualified crew in database</p>
                ) : (
                  <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={sicId} onChange={(e) => setSicId(e.target.value)}>
                    <option value="">Select SIC...</option>
                    {eligibleCrew.filter((c) => c.id !== picId).map((c) => (
                      <option key={c.id} value={c.id}>{c.display_name} ({c.role})</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={() => setStep(2)} disabled={!acId}>Next: Route Legs</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 2: Route Legs ─────────────────────────────────────────── */}
      {step === 2 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Route className="h-5 w-5 text-brand-400" /> Flight Legs
            </h2>
            <p className="text-xs text-muted-foreground">Enter <AcronymSpan text="ICAO" /> codes. Distances will be calculated automatically.</p>
            <div className="space-y-3">
              {legs.map((leg, i) => (
                <div key={i} className="rounded-md border border-border/50 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium">Leg {leg.leg_number}</span>
                    {legs.length > 1 && (
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeLeg(i)}>
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted-foreground">From</label>
                      <Input value={leg.departure} onChange={(e) => updateLeg(i, 'departure', e.target.value)}
                        placeholder="MYNN" disabled={i > 0} className={i > 0 ? 'opacity-60' : ''} maxLength={4} />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">To</label>
                      <Input value={leg.arrival} onChange={(e) => updateLeg(i, 'arrival', e.target.value)}
                        placeholder="MTPP" maxLength={4} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" size="sm" onClick={addLeg} className="w-full">
              <Plus className="mr-2 h-4 w-4" /> Add Leg
            </Button>

            {planError && (
              <div className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {planError}
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={callRoutePlanner} disabled={planLoading || !legs.some(l => l.departure && l.arrival)}>
                {planLoading ? 'Planning...' : 'Plan Route'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 3: Route Plan Review ──────────────────────────────────── */}
      {step === 3 && routePlan && (
        <div className="space-y-4">
          {/* Totals banner */}
          <Card>
            <CardContent className="p-4">
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-brand-400">{Math.round(routePlan.totals?.total_distance_nm || 0)}</p>
                  <p className="text-xs text-muted-foreground">Total nm</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-brand-400">{routePlan.totals?.total_block_hours?.toFixed(1) || '0'}</p>
                  <p className="text-xs text-muted-foreground">Block hours</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-brand-400">{Math.round(routePlan.totals?.total_fuel_gal || 0)}</p>
                  <p className="text-xs text-muted-foreground">Fuel (gal)</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-brand-400">{routePlan.totals?.total_flight_time_min || 0}</p>
                  <p className="text-xs text-muted-foreground">Flight min</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Warnings */}
          {routePlan.flags?.warnings?.length > 0 && (
            <Card className="border-amber-500/20">
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2 text-amber-500"><FileWarning className="h-4 w-4" /> Warnings</CardTitle></CardHeader>
              <CardContent className="space-y-1">
                {routePlan.flags.warnings.map((w: string, i: number) => (
                  <div key={i} className="rounded-md bg-amber-500/5 px-3 py-1.5 text-xs text-amber-500">{w}</div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Critical flags */}
          {routePlan.flags?.critical?.length > 0 && (
            <Card className="border-red-500/20">
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2 text-red-500"><AlertTriangle className="h-4 w-4" /> Critical Issues</CardTitle></CardHeader>
              <CardContent className="space-y-1">
                {routePlan.flags.critical.map((f: string, i: number) => (
                  <div key={i} className="rounded-md bg-red-500/5 px-3 py-1.5 text-xs text-red-500">{f}</div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Flags badges */}
          <div className="flex flex-wrap gap-2">
            {routePlan.flags?.overnight_required && <Badge variant="outline" className="bg-blue-500/10 text-blue-500">Overnight required</Badge>}
            {routePlan.flags?.crew_swap_required && <Badge variant="outline" className="bg-amber-500/10 text-amber-500">Crew swap needed</Badge>}
            {routePlan.flags?.fuel_stop_required && <Badge variant="outline" className="bg-red-500/10 text-red-500">Fuel stop required</Badge>}
          </div>

          {/* Per-leg details */}
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Leg Details</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {routePlan.legs.map((leg: any, i: number) => (
                <div key={i} className="rounded-md border border-border/50 p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{leg.origin} → {leg.destination}</p>
                    <Badge variant="outline" className={leg.is_ok ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}>
                      {leg.is_ok ? 'OK' : 'ISSUES'}
                    </Badge>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>{leg.distance_nm} nm</span>
                    <span>{leg.block_time_min} min block</span>
                    <span>{leg.fuel_gal} gal</span>
                    {leg.destination_intel?.weather?.flight_category && (
                      <span className={`font-medium ${
                        leg.destination_intel.weather.flight_category === 'VFR' ? 'text-green-500' :
                        leg.destination_intel.weather.flight_category === 'MVFR' ? 'text-blue-500' :
                        leg.destination_intel.weather.flight_category === 'IFR' ? 'text-red-500' : 'text-pink-500'
                      }`}>
                        <Acronym>{leg.destination_intel.weather.flight_category}</Acronym>
                      </span>
                    )}
                  </div>
                  {leg.flags?.length > 0 && (
                    <div className="mt-1 space-y-0.5">
                      {leg.flags.map((f: string, fi: number) => (
                        <p key={fi} className="text-xs text-amber-500">{f}</p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Crew duty */}
          {routePlan.crew_duty && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Clock className="h-4 w-4 text-brand-400" /> Crew Duty</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-3 gap-3 text-xs">
                <div><span className="text-muted-foreground">Mission:</span> {routePlan.crew_duty.total_duty_min || 0} min</div>
                <div><span className="text-muted-foreground">Max:</span> {routePlan.crew_duty.max_duty_min || '—'} min</div>
                <div><Badge variant="outline" className={
                  routePlan.crew_duty.within_limits !== false ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
                }>{routePlan.crew_duty.within_limits !== false ? 'Within limits' : 'Over limit'}</Badge></div>
              </CardContent>
            </Card>
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>Back: Legs</Button>
            <Button onClick={() => setStep(4)}>Next: Passengers</Button>
          </div>
        </div>
      )}

      {/* ── Step 4: Passengers ─────────────────────────────────────────── */}
      {step === 4 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Users className="h-5 w-5 text-brand-400" /> Passengers & Cargo
            </h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search existing passengers..."
                value={paxSearch} onChange={async (e) => {
                  const val = e.target.value
                  setPaxSearch(val)
                  if (val.length < 2) { setPaxResults([]); return }
                  try {
                    const res = await api.get(`/api/v1/passengers/search/quick?q=${encodeURIComponent(val)}`)
                    setPaxResults(res.data)
                  } catch { setPaxResults([]) }
                }} />
              {paxResults.length > 0 && (
                <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-background shadow-lg">
                  {paxResults.map((r: any) => (
                    <button key={r.id} type="button"
                      className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-accent"
                      onClick={() => {
                        if (!passengers.find(p => p.name === r.full_name)) {
                          setPassengers([...passengers, { name: r.full_name, nationality: r.nationality || '', weight: r.weight_kg?.toString() || '' }])
                        }
                        setPaxSearch('')
                        setPaxResults([])
                      }}>
                      <span className="font-medium">{r.full_name}</span>
                      <span className="text-xs text-muted-foreground">{r.nationality}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="text-center text-xs text-muted-foreground">— or add new —</div>
            {passengers.length === 0 ? (
              <p className="text-sm text-muted-foreground">No passengers added yet.</p>
            ) : (
              <div className="space-y-2">
                {passengers.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-md border border-border/50 p-2">
                    <Input className="flex-1" placeholder="Name" value={p.name} onChange={(e) => updatePax(i, 'name', e.target.value)} />
                    <Input className="w-20" placeholder="Nat" value={p.nationality} onChange={(e) => updatePax(i, 'nationality', e.target.value.toUpperCase())} />
                    <Input className="w-20" type="number" placeholder="kg" value={p.weight} onChange={(e) => updatePax(i, 'weight', e.target.value)} />
                    <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => removePax(i)}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            <Button variant="outline" size="sm" onClick={addPassenger}><Plus className="mr-2 h-4 w-4" /> Add Manually</Button>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(3)}>Back</Button>
              <Button onClick={handleCreate} disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Mission'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 5: Created ────────────────────────────────────────────── */}
      {step === 5 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-green-500">
              <Plane className="h-5 w-5" /> Mission Created
            </h2>
            {routePlan && (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3 text-sm space-y-1">
                <div className="flex justify-between"><span className="text-muted-foreground">Distance</span> <span className="font-medium">{Math.round(routePlan.totals?.total_distance_nm || 0)} nm</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Block time</span> <span className="font-medium">{routePlan.totals?.total_block_hours?.toFixed(1)}h</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Fuel</span> <span className="font-medium">{Math.round(routePlan.totals?.total_fuel_gal || 0)} gal</span></div>
              </div>
            )}
            {createWarnings.length > 0 && (
              <div className="space-y-1">
                <p className="flex items-center gap-2 text-sm font-medium text-amber-500"><FileWarning className="h-4 w-4" /> Warnings</p>
                {createWarnings.map((w, i) => (
                  <div key={i} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2 text-sm text-amber-500">{w}</div>
                ))}
              </div>
            )}
            {createWarnings.length === 0 && <p className="text-sm text-green-500">All checks passed — no warnings.</p>}
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => navigate(`/missions/${missionId}`)}>View Mission</Button>
              <Button onClick={() => navigate('/missions')}>Back to Missions</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
