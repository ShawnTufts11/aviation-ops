import { useState, useEffect } from 'react'
import {
  Plane, Wrench, Users, History, Calendar,
  AlertTriangle, Clock, ArrowRight, Siren,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import { Link } from 'react-router-dom'
import api from '@/lib/api'
import LiveTrackingMap from '@/features/tracking/LiveTrackingMap'
import { AcronymSpan } from '@/components/ui/acronym'

interface Aircraft {
  id: string; tail_number: string; make: string; model: string; status: string; base: string
}
interface Flight {
  id: string; departure_airport: string; arrival_airport: string; status: string
  scheduled_departure: string | null; flight_number: string | null
}
interface CrewSummary {
  total_active: number; expiring_medical: number; expiring_license: number
}

export default function DashboardPage() {
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [flights, setFlights] = useState<Flight[]>([])
  const [activeFlights, setActiveFlights] = useState<Flight[]>([])
  const [mxOverdue, setMxOverdue] = useState(0)
  const [mxDueSoon, setMxDueSoon] = useState(0)
  const [crewSummary, setCrewSummary] = useState<CrewSummary | null>(null)
  const [emergencies, setEmergencies] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showEmergencyDialog, setShowEmergencyDialog] = useState(false)
  const [emergencyTitle, setEmergencyTitle] = useState('')
  const [emergencyDesc, setEmergencyDesc] = useState('')
  const [emergencySubmitting, setEmergencySubmitting] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/aircraft?per_page=100'),
      api.get('/api/v1/flights/today'),
      api.get('/api/v1/flights/active'),
      api.get('/api/v1/maintenance?per_page=1'),
      api.get('/api/v1/crew/summary/counts'),
      api.get('/api/v1/comms/emergency/active'),
    ]).then(([acRes, flRes, actRes, mxRes, crewRes, emRes]) => {
      setAircraft(acRes.data.data)
      setFlights(flRes.data)
      setActiveFlights(actRes.data)
      setMxOverdue(mxRes.data.overdue_count)
      setMxDueSoon(mxRes.data.due_soon_count)
      setCrewSummary(crewRes.data)
      setEmergencies(emRes.data || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const now = new Date()
  const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

  if (loading) return (
    <div className="space-y-6">
      <div className="h-8 w-64 animate-pulse rounded bg-muted" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1,2,3,4].map((i) => <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-16 rounded bg-muted" /></CardContent></Card>)}
      </div>
    </div>
  )

  const activeCount = aircraft.filter((a) => a.status === 'active').length
  const inMxCount = aircraft.filter((a) => a.status === 'in_maintenance').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Operation Center</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" /> {dateStr}
          </p>
        </div>
        <Button
          variant="destructive"
          onClick={() => setShowEmergencyDialog(true)}
          className="gap-2"
        >
          <Siren className="h-4 w-4" /> Emergency
        </Button>
      </div>

      {/* Active flights banner */}
      {activeFlights.length > 0 && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-green-500">
            <Plane className="h-4 w-4 animate-pulse" />
            {activeFlights.length} Active Flight{activeFlights.length > 1 ? 's' : ''}
          </div>
          <div className="mt-2 space-y-1">
            {activeFlights.map((f) => (
              <div key={f.id} className="text-sm text-muted-foreground">
                {f.departure_airport} → {f.arrival_airport}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link to="/fleet">
          <Card className="cursor-pointer transition-colors hover:border-brand-500/50">
            <CardContent className="flex items-center gap-3 p-4">
              <Plane className="h-8 w-8 text-brand-400" />
              <div>
                <p className="text-2xl font-bold">{activeCount}</p>
                <p className="text-sm text-muted-foreground">Active Aircraft</p>
                {inMxCount > 0 && <p className="text-xs text-amber-500">{inMxCount} in maintenance</p>}
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/flights">
          <Card className="cursor-pointer transition-colors hover:border-brand-500/50">
            <CardContent className="flex items-center gap-3 p-4">
              <History className="h-8 w-8 text-cyan-400" />
              <div>
                <p className="text-2xl font-bold">{flights.length}</p>
                <p className="text-sm text-muted-foreground">Today's Flights</p>
                {activeFlights.length > 0 && <p className="text-xs text-green-500">{activeFlights.length} active</p>}
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/maintenance">
          <Card className={`cursor-pointer transition-colors ${mxOverdue > 0 ? 'border-red-500/30 hover:border-red-500/50' : 'hover:border-brand-500/50'}`}>
            <CardContent className="flex items-center gap-3 p-4">
              <Wrench className={`h-8 w-8 ${mxOverdue > 0 ? 'text-red-500' : 'text-amber-400'}`} />
              <div>
                <p className="text-2xl font-bold">{mxOverdue + mxDueSoon}</p>
                <p className="text-sm text-muted-foreground">Maintenance Due</p>
                {mxOverdue > 0 && <p className="text-xs text-red-500">{mxOverdue} overdue</p>}
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link to="/crew">
          <Card className="cursor-pointer transition-colors hover:border-brand-500/50">
            <CardContent className="flex items-center gap-3 p-4">
              <Users className="h-8 w-8 text-purple-400" />
              <div>
                <p className="text-2xl font-bold">{crewSummary?.total_active || 0}</p>
                <p className="text-sm text-muted-foreground"><AcronymSpan text="Crew Active" /></p>
                {(crewSummary?.expiring_medical || 0) > 0 && (
                  <p className="text-xs text-amber-500">{crewSummary?.expiring_medical} <AcronymSpan text="medical" />s expiring</p>
                )}
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Today's schedule */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Today's Schedule</CardTitle>
            <Link to="/flights">
              <Button variant="ghost" size="sm">View All <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
            </Link>
          </CardHeader>
          <CardContent>
            {flights.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No flights scheduled today</p>
            ) : (
              <div className="space-y-2">
                {flights.slice(0, 5).map((f) => (
                  <div key={f.id} className="flex items-center justify-between rounded-md bg-muted/30 px-3 py-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{f.departure_airport}</span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-medium">{f.arrival_airport}</span>
                    </div>
                    <Badge variant={
                      f.status === 'active' ? 'default' :
                      f.status === 'completed' ? 'outline' : 'secondary'
                    } className={
                      f.status === 'active' ? 'bg-green-500' : ''
                    }>
                      {f.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts & notifications */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {mxOverdue > 0 && (
              <div className="flex items-start gap-3 rounded-md border border-red-500/20 bg-red-500/5 p-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                <div className="text-sm">
                  <p className="font-medium text-red-500">{mxOverdue} overdue maintenance tasks</p>
                  {mxDueSoon > 0 && <p className="text-muted-foreground">{mxDueSoon} more due within 30 days</p>}
                </div>
              </div>
            )}
            {(crewSummary?.expiring_medical || 0) > 0 && (
              <div className="flex items-start gap-3 rounded-md border border-amber-500/20 bg-amber-500/5 p-3">
                <Clock className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                <div className="text-sm">
                  <p className="font-medium text-amber-500">{crewSummary?.expiring_medical} medicals expiring within 30 days</p>
                </div>
              </div>
            )}
            {mxOverdue === 0 && mxDueSoon === 0 && (crewSummary?.expiring_medical || 0) === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">No current alerts — all clear</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Live Tracking Map */}
      <LiveTrackingMap />

      {/* Fleet status */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Fleet Status</CardTitle>
          <Link to="/fleet">
            <Button variant="ghost" size="sm">Manage <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {aircraft.map((ac) => (
              <Link key={ac.id} to={`/fleet/${ac.id}`}>
                <div className="rounded-md border border-border/50 p-3 text-sm transition-colors hover:border-brand-500/50 hover:bg-brand-500/5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{ac.tail_number}</span>
                    <span className={`inline-flex h-2 w-2 rounded-full ${
                      ac.status === 'active' ? 'bg-green-500' :
                      ac.status === 'in_maintenance' ? 'bg-amber-500' : 'bg-red-500'
                    }`} />
                  </div>
                  <p className="text-xs text-muted-foreground">{ac.make} {ac.model}</p>
                  <p className="text-xs text-muted-foreground">Base: {ac.base}</p>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Emergency alerts banner */}
      {emergencies.length > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-red-500">
            <Siren className="h-4 w-4 animate-pulse" />
            Active Emergency
          </div>
          {emergencies.map((e: any) => (
            <div key={e.id} className="mt-2 flex items-center justify-between text-sm">
              <span className="font-medium">{e.title}</span>
              <Button
                size="sm"
                variant="outline"
                className="text-red-500"
                onClick={async () => {
                  await api.post(`/api/v1/comms/emergency/${e.id}/acknowledge`)
                  setEmergencies((prev: any[]) => prev.filter((a: any) => a.id !== e.id))
                }}
              >
                Acknowledge
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Emergency Alert Dialog */}
      <Dialog open={showEmergencyDialog} onOpenChange={setShowEmergencyDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-500">
              <Siren className="h-5 w-5" /> Trigger Emergency Alert
            </DialogTitle>
            <DialogDescription>This will notify all active users immediately.</DialogDescription>
          </DialogHeader>
          <form onSubmit={async (e) => {
            e.preventDefault()
            setEmergencySubmitting(true)
            try {
              await api.post('/api/v1/comms/emergency', {
                title: emergencyTitle,
                description: emergencyDesc || null,
              })
              setShowEmergencyDialog(false)
              setEmergencyTitle('')
              setEmergencyDesc('')
              window.location.reload()
            } catch { /* silent */ }
            setEmergencySubmitting(false)
          }} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Alert Title</label>
              <Input value={emergencyTitle} onChange={(e) => setEmergencyTitle(e.target.value)} placeholder="e.g., Aircraft incident at MYNN" required />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={emergencyDesc}
                onChange={(e) => setEmergencyDesc(e.target.value)}
                placeholder="Brief description of the situation..."
              />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowEmergencyDialog(false)}>Cancel</Button>
              <Button type="submit" variant="destructive" disabled={emergencySubmitting}>
                {emergencySubmitting ? 'Sending...' : 'Trigger Alert'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
