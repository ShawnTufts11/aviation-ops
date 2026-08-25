import { useState, useEffect, type FormEvent } from 'react'
import { History, Plus, Plane, PlaneTakeoff, PlaneLanding, XCircle, DollarSign } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface Flight {
  id: string
  flight_number: string | null
  flight_type: string
  status: string
  departure_airport: string
  arrival_airport: string
  aircraft_id: string | null
  scheduled_departure: string | null
  scheduled_arrival: string | null
  actual_departure: string | null
  actual_arrival: string | null
  pilot_in_command: string | null
  passengers_count: number | null
  notes: string | null
}

interface Aircraft {
  id: string
  tail_number: string
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  scheduled: { label: 'Scheduled', color: 'bg-blue-500/10 text-blue-500' },
  active: { label: 'Active', color: 'bg-green-500/10 text-green-500' },
  completed: { label: 'Completed', color: 'bg-muted text-muted-foreground' },
  cancelled: { label: 'Cancelled', color: 'bg-red-500/10 text-red-500' },
  diverted: { label: 'Diverted', color: 'bg-amber-500/10 text-amber-500' },
}

function fmtDate(d: string | null) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

export default function FlightsPage() {
  const [flights, setFlights] = useState<Flight[]>([])
  const [activeFlights, setActiveFlights] = useState<Flight[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('today')
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [showAdd, setShowAdd] = useState(false)

  // Add form
  const [dep, setDep] = useState('')
  const [arr, setArr] = useState('')
  const [acId, setAcId] = useState('')
  const [schedDep, setSchedDep] = useState('')
  const [pax, setPax] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [mxWarnings, setMxWarnings] = useState<string[]>([])

  // Cost reconciliation state
  const [showCostDialog, setShowCostDialog] = useState(false)
  const [costFlight, setCostFlight] = useState<Flight | null>(null)
  const [estimatedCosts, setEstimatedCosts] = useState<{
    legs: { origin: string; destination: string; landing_fee_usd: number; overnight_parking_usd: number; handling_fee_usd: number; customs_fee_usd: number; estimated_cash_needed: number }[]
    estimated_total_cash_needed: number
  } | null>(null)
  const [actualLanding, setActualLanding] = useState('')
  const [actualParking, setActualParking] = useState('')
  const [actualHandling, setActualHandling] = useState('')
  const [actualCustoms, setActualCustoms] = useState('')
  const [costSaving, setCostSaving] = useState(false)
  const [costError, setCostError] = useState<string | null>(null)

  // Run pre-flight checks when aircraft + route selected
  useEffect(() => {
    if (!acId || !dep || !arr) { setMxWarnings([]); return }
    const timer = setTimeout(async () => {
      try {
        const res = await api.get('/api/v1/ops-checks/maintenance-conflicts', {
          params: { aircraft_id: acId },
        })
        if (res.data.has_conflicts) {
          const warns: string[] = []
          if (res.data.severity === 'critical') {
            warns.push(`⚠ ${res.data.overdue_count} overdue maintenance items — resolve before flight`)
          }
          if (res.data.total_open > (res.data.overdue_count || 0)) {
            warns.push(`🟡 ${res.data.total_open} open maintenance tasks`)
          }
          setMxWarnings(warns)
        } else {
          setMxWarnings([])
        }
      } catch { /* silent */ }
    }, 500)
    return () => clearTimeout(timer)
  }, [acId, dep, arr])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [activeRes, todayRes] = await Promise.all([
        api.get('/api/v1/flights/active'),
        api.get('/api/v1/flights/today'),
      ])
      setActiveFlights(activeRes.data)
      setFlights(todayRes.data)
      setTotal(todayRes.data.length)
    } catch { /* silent */ }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
    api.get('/api/v1/aircraft?per_page=100').then((r) => setAircraft(r.data.data))
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/v1/flights', {
        departure_airport: dep,
        arrival_airport: arr,
        aircraft_id: acId || undefined,
        scheduled_departure: schedDep ? new Date(schedDep).toISOString() : undefined,
        passengers_count: pax ? parseInt(pax) : undefined,
      })
      setShowAdd(false)
      setDep(''); setArr(''); setAcId(''); setSchedDep(''); setPax('')
      await fetchData()
    } catch { /* silent */ }
    setSubmitting(false)
  }

  const handleStatus = async (id: string, status: string) => {
    try {
      await api.patch(`/api/v1/flights/${id}`, { status })
      await fetchData()
    } catch { /* silent */ }
  }

  const handleOpenCosts = async (f: Flight) => {
    setCostFlight(f)
    setActualLanding('')
    setActualParking('')
    setActualHandling('')
    setActualCustoms('')
    setCostError(null)
    setCostSaving(false)
    setEstimatedCosts(null)
    setShowCostDialog(true)

    // Try to get estimated costs from route planner
    try {
      const res = await api.post('/api/v1/routes/plan', {
        flight_id: f.id,
      })
      if (res.data?.estimated_total_cash_needed) {
        const legs = (res.data.legs || []).map((leg: Record<string, unknown>) => ({
          origin: (leg.origin as string) || '',
          destination: (leg.destination as string) || '',
          landing_fee_usd: (leg.landing_fee_usd as number) || 0,
          overnight_parking_usd: (leg.overnight_parking_usd as number) || 0,
          handling_fee_usd: (leg.handling_fee_usd as number) || 0,
          customs_fee_usd: (leg.customs_fee_usd as number) || 0,
          estimated_cash_needed: (leg.estimated_cash_needed as number) || 0,
        }))
        setEstimatedCosts({
          legs,
          estimated_total_cash_needed: res.data.estimated_total_cash_needed as number,
        })
      } else {
        // Fallback: build from departure/arrival airports
        setEstimatedCosts({
          legs: [{
            origin: f.departure_airport,
            destination: f.arrival_airport,
            landing_fee_usd: 250,
            overnight_parking_usd: 0,
            handling_fee_usd: 200,
            customs_fee_usd: 50,
            estimated_cash_needed: 500,
          }],
          estimated_total_cash_needed: 500,
        })
      }
    } catch {
      // Fallback estimate
      setEstimatedCosts({
        legs: [{
          origin: f.departure_airport,
          destination: f.arrival_airport,
          landing_fee_usd: 250,
          overnight_parking_usd: 0,
          handling_fee_usd: 200,
          customs_fee_usd: 50,
          estimated_cash_needed: 500,
        }],
        estimated_total_cash_needed: 500,
      })
    }

    // Also try to fetch existing actual costs
    try {
      const costsRes = await api.get(`/api/v1/flights/${f.id}/costs`)
      if (costsRes.data?.actual) {
        setActualLanding(String(costsRes.data.actual.landing_fee_usd || ''))
        setActualParking(String(costsRes.data.actual.overnight_parking_usd || ''))
        setActualHandling(String(costsRes.data.actual.handling_fee_usd || ''))
        setActualCustoms(String(costsRes.data.actual.customs_fee_usd || ''))
      }
    } catch { /* silent */ }
  }

  const handleSaveActuals = async () => {
    if (!costFlight) return
    setCostSaving(true)
    setCostError(null)
    try {
      await api.post(`/api/v1/flights/${costFlight.id}/actual-costs`, {
        landing_fee_usd: parseFloat(actualLanding) || 0,
        overnight_parking_usd: parseFloat(actualParking) || 0,
        handling_fee_usd: parseFloat(actualHandling) || 0,
        customs_fee_usd: parseFloat(actualCustoms) || 0,
      })
      setShowCostDialog(false)
    } catch {
      setCostError('Failed to save actual costs. Is the backend running?')
    }
    setCostSaving(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Flights</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {activeFlights.length > 0
              ? `${activeFlights.length} active · ${total} today`
              : `${total} flights today`}
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> New Flight
        </Button>
      </div>

      {/* Active flights banner */}
      {activeFlights.length > 0 && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-green-500">
            <Plane className="h-4 w-4 animate-pulse" />
            Active Flights
          </div>
          <div className="mt-2 space-y-2">
            {activeFlights.map((f) => (
              <div key={f.id} className="flex items-center justify-between rounded-md bg-background/50 px-3 py-2 text-sm">
                <span className="font-medium">{f.departure_airport} → {f.arrival_airport}</span>
                <span className="text-muted-foreground">{fmtDate(f.scheduled_departure)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="today">Today ({total})</TabsTrigger>
          <TabsTrigger value="active">Active ({activeFlights.length})</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          {loading ? (
            <div className="space-y-3">{[1,2,3].map((i) => (
              <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-16 rounded bg-muted" /></CardContent></Card>
            ))}</div>
          ) : flights.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <History className="h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">No flights today</p>
              <Button onClick={() => setShowAdd(true)}>
                <Plus className="mr-2 h-4 w-4" /> Schedule Flight
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {(activeTab === 'active' ? activeFlights : flights).map((f) => {
                const cfg = STATUS_CONFIG[f.status] || { label: f.status, color: '' }
                const tail = aircraft.find((a) => a.id === f.aircraft_id)?.tail_number
                return (
                  <Card key={f.id} className="border-border/50">
                    <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <PlaneTakeoff className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{f.departure_airport}</span>
                          <span className="text-muted-foreground">→</span>
                          <PlaneLanding className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{f.arrival_airport}</span>
                          <Badge variant="outline" className={cfg.color}>{cfg.label}</Badge>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                          {f.flight_number && <span className="font-mono text-xs">{f.flight_number}</span>}
                          {tail && <span>{tail}</span>}
                          <span>Dep: {fmtDate(f.scheduled_departure)}</span>
                          <span>Arr: {fmtDate(f.scheduled_arrival)}</span>
                          {f.passengers_count != null && <span>{f.passengers_count} pax</span>}
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <Button size="sm" variant="ghost" className="text-xs text-muted-foreground" onClick={() => handleOpenCosts(f)}>
                          <DollarSign className="mr-1 h-3.5 w-3.5" /> Costs
                        </Button>
                        {f.status === 'scheduled' && (
                          <>
                            <Button size="sm" variant="outline" className="text-green-500" onClick={() => handleStatus(f.id, 'active')}>
                              <PlaneTakeoff className="mr-1 h-3.5 w-3.5" /> Depart
                            </Button>
                            <Button size="sm" variant="outline" className="text-red-500" onClick={() => handleStatus(f.id, 'cancelled')}>
                              <XCircle className="mr-1 h-3.5 w-3.5" />
                            </Button>
                          </>
                        )}
                        {f.status === 'active' && (
                          <Button size="sm" variant="outline" className="text-green-500" onClick={() => handleStatus(f.id, 'completed')}>
                            <PlaneLanding className="mr-1 h-3.5 w-3.5" /> Land
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* New Flight Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Flight</DialogTitle>
            <DialogDescription>Create a new flight leg.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            {/* Pre-flight warnings */}
            {mxWarnings.length > 0 && (
              <div className="space-y-2">
                {mxWarnings.map((w: any, i: number) => (
                  <div key={i} className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
                    w.includes('⛔') ? 'border-red-500/20 bg-red-500/5 text-red-500' :
                    w.startsWith('⚠') ? 'border-red-500/20 bg-red-500/5 text-red-500' :
                    w.startsWith('🟡') ? 'border-amber-500/20 bg-amber-500/5 text-amber-500' :
                    'border-amber-500/20 bg-amber-500/5 text-amber-500'
                  }`}>
                    <span className="text-base leading-none">{w[0]}</span>
                    <span>{w.slice(2)}</span>
                  </div>
                ))}
              </div>
            )}
            {mxWarnings.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Resolve conflicts before dispatching. Check Maintenance page for details.
              </p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Departure (ICAO)</label>
                <Input placeholder="MYNN" value={dep} onChange={(e) => setDep(e.target.value.toUpperCase())} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Arrival (ICAO)</label>
                <Input placeholder="MTPP" value={arr} onChange={(e) => setArr(e.target.value.toUpperCase())} required />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Aircraft</label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={acId} onChange={(e) => setAcId(e.target.value)}>
                <option value="">Select aircraft...</option>
                {aircraft.map((a) => (
                  <option key={a.id} value={a.id}>{a.tail_number}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Departure Time</label>
                <Input type="datetime-local" value={schedDep} onChange={(e) => setSchedDep(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Passengers</label>
                <Input type="number" min={0} placeholder="0" value={pax} onChange={(e) => setPax(e.target.value)} />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Scheduling...' : 'Schedule Flight'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Cost Reconciliation Dialog */}
      <Dialog open={showCostDialog} onOpenChange={setShowCostDialog}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Cost Reconciliation</DialogTitle>
            <DialogDescription>
              {costFlight ? `${costFlight.departure_airport} → ${costFlight.arrival_airport}` : ''}
            </DialogDescription>
          </DialogHeader>

          {estimatedCosts && (
            <div className="space-y-4">
              {/* Estimated Costs */}
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">Estimated Costs</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground">
                        <th className="py-1.5 pr-2 font-medium text-xs">Route</th>
                        <th className="py-1.5 pr-2 font-medium text-xs">Landing</th>
                        <th className="py-1.5 pr-2 font-medium text-xs">Parking</th>
                        <th className="py-1.5 pr-2 font-medium text-xs">Handling</th>
                        <th className="py-1.5 pr-2 font-medium text-xs">Customs</th>
                        <th className="py-1.5 font-medium text-xs">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {estimatedCosts.legs.map((leg, i) => (
                        <tr key={i} className="border-b border-border/20">
                          <td className="py-1.5 pr-2 text-xs font-medium">{leg.origin}→{leg.destination}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${leg.landing_fee_usd}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${leg.overnight_parking_usd}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${leg.handling_fee_usd}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${leg.customs_fee_usd}</td>
                          <td className="py-1.5 font-mono text-xs font-medium">${leg.estimated_cash_needed}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-border/50 font-medium">
                        <td colSpan={5} className="py-1.5 pr-2 text-right text-xs">Total Estimated:</td>
                        <td className="py-1.5 font-mono text-xs font-bold">${estimatedCosts.estimated_total_cash_needed}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              <hr className="border-border/30" />

              {/* Actual Costs Form */}
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">Actual Costs Incurred</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium">Landing Fee ($)</label>
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="0.00"
                      value={actualLanding}
                      onChange={(e) => setActualLanding(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium">Parking ($)</label>
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="0.00"
                      value={actualParking}
                      onChange={(e) => setActualParking(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium">Handling ($)</label>
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="0.00"
                      value={actualHandling}
                      onChange={(e) => setActualHandling(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium">Customs ($)</label>
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="0.00"
                      value={actualCustoms}
                      onChange={(e) => setActualCustoms(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Variance */}
              {(() => {
                const aLand = parseFloat(actualLanding) || 0
                const aPark = parseFloat(actualParking) || 0
                const aHand = parseFloat(actualHandling) || 0
                const aCust = parseFloat(actualCustoms) || 0
                const actualTotal = aLand + aPark + aHand + aCust
                const totalEst = estimatedCosts.estimated_total_cash_needed
                const variance = actualTotal - totalEst
                return (
                  <div>
                    <h4 className="mb-2 text-sm font-medium text-muted-foreground">Variance</h4>
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-border/50 text-muted-foreground">
                          <th className="py-1.5 pr-2 font-medium text-xs">Category</th>
                          <th className="py-1.5 pr-2 font-medium text-xs">Estimated</th>
                          <th className="py-1.5 pr-2 font-medium text-xs">Actual</th>
                          <th className="py-1.5 font-medium text-xs">Variance</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-border/20">
                          <td className="py-1.5 pr-2 text-xs">Landing Fee</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${estimatedCosts.legs.reduce((s, l) => s + l.landing_fee_usd, 0)}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${aLand}</td>
                          <td className={`py-1.5 font-mono text-xs ${aLand - estimatedCosts.legs.reduce((s, l) => s + l.landing_fee_usd, 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            ${(aLand - estimatedCosts.legs.reduce((s, l) => s + l.landing_fee_usd, 0)).toFixed(2)}
                          </td>
                        </tr>
                        <tr className="border-b border-border/20">
                          <td className="py-1.5 pr-2 text-xs">Parking</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${estimatedCosts.legs.reduce((s, l) => s + l.overnight_parking_usd, 0)}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${aPark}</td>
                          <td className={`py-1.5 font-mono text-xs ${aPark - estimatedCosts.legs.reduce((s, l) => s + l.overnight_parking_usd, 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            ${(aPark - estimatedCosts.legs.reduce((s, l) => s + l.overnight_parking_usd, 0)).toFixed(2)}
                          </td>
                        </tr>
                        <tr className="border-b border-border/20">
                          <td className="py-1.5 pr-2 text-xs">Handling</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${estimatedCosts.legs.reduce((s, l) => s + l.handling_fee_usd, 0)}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${aHand}</td>
                          <td className={`py-1.5 font-mono text-xs ${aHand - estimatedCosts.legs.reduce((s, l) => s + l.handling_fee_usd, 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            ${(aHand - estimatedCosts.legs.reduce((s, l) => s + l.handling_fee_usd, 0)).toFixed(2)}
                          </td>
                        </tr>
                        <tr className="border-b border-border/20">
                          <td className="py-1.5 pr-2 text-xs">Customs</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${estimatedCosts.legs.reduce((s, l) => s + l.customs_fee_usd, 0)}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${aCust}</td>
                          <td className={`py-1.5 font-mono text-xs ${aCust - estimatedCosts.legs.reduce((s, l) => s + l.customs_fee_usd, 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            ${(aCust - estimatedCosts.legs.reduce((s, l) => s + l.customs_fee_usd, 0)).toFixed(2)}
                          </td>
                        </tr>
                      </tbody>
                      <tfoot>
                        <tr className="border-t border-border/50 font-medium">
                          <td className="py-1.5 pr-2 text-xs">Total</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${totalEst}</td>
                          <td className="py-1.5 pr-2 font-mono text-xs">${actualTotal.toFixed(2)}</td>
                          <td className={`py-1.5 font-mono text-xs font-bold ${variance > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            ${variance.toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )
              })()}

              {costError && (
                <div className="rounded-md border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">
                  {costError}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => setShowCostDialog(false)}>Close</Button>
                <Button onClick={handleSaveActuals} disabled={costSaving}>
                  {costSaving ? 'Saving...' : 'Save Actuals'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
