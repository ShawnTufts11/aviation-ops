import { useState, useEffect, type FormEvent } from 'react'
import { History, Plus, Plane, PlaneTakeoff, PlaneLanding, XCircle } from 'lucide-react'
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
    </div>
  )
}
