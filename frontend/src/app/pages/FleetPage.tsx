import { useState, useEffect, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Plane, Plus, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import api from '@/lib/api'

type AircraftStatus = 'active' | 'in_maintenance' | 'grounded' | 'retired'

interface Aircraft {
  id: string
  tail_number: string
  make: string
  model: string
  year: number
  status: AircraftStatus
  base: string
  total_airframe_hours: number | null
  total_cycles: number | null
  max_seats: number
  max_cargo_kg: number | null
  registration_expiry: string | null
  created_at: string
}

const STATUS_CONFIG: Record<AircraftStatus, { label: string; color: string }> = {
  active: { label: 'Active', color: 'bg-green-500/10 text-green-500 border-green-500/20' },
  in_maintenance: { label: 'In Mx', color: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
  grounded: { label: 'Grounded', color: 'bg-red-500/10 text-red-500 border-red-500/20' },
  retired: { label: 'Retired', color: 'bg-muted text-muted-foreground border-border' },
}

function StatusBadge({ status }: { status: AircraftStatus }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.grounded
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.color}`}>
      <span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${
        status === 'active' ? 'bg-green-500' :
        status === 'in_maintenance' ? 'bg-amber-500' :
        status === 'grounded' ? 'bg-red-500' : 'bg-muted-foreground'
      }`} />
      {cfg.label}
    </span>
  )
}

export default function FleetPage() {
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showAddDialog, setShowAddDialog] = useState(false)

  // Add form state
  const [tailNumber, setTailNumber] = useState('')
  const [acMake, setAcMake] = useState('')
  const [acModel, setAcModel] = useState('')
  const [acYear, setAcYear] = useState(new Date().getFullYear().toString())
  const [acBase, setAcBase] = useState('')
  const [acSeats, setAcSeats] = useState('1')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  const fetchAircraft = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter) params.set('status', statusFilter)
      if (search) params.set('q', search)
      const res = await api.get(`/api/v1/aircraft?${params}`)
      setAircraft(res.data.data)
      setTotal(res.data.total)
    } catch {
      // silent
    }
    setLoading(false)
  }

  useEffect(() => { fetchAircraft() }, [statusFilter])

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    fetchAircraft()
  }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setFormError('')
    setSubmitting(true)
    try {
      await api.post('/api/v1/aircraft', {
        tail_number: tailNumber,
        make: acMake,
        model: acModel,
        year: parseInt(acYear),
        max_seats: parseInt(acSeats),
        base: acBase,
        home_airport: acBase,
      })
      setShowAddDialog(false)
      setTailNumber('')
      setAcMake('')
      setAcModel('')
      setAcYear(new Date().getFullYear().toString())
      setAcBase('')
      setAcSeats('1')
      await fetchAircraft()
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || 'Failed to add aircraft')
    }
    setSubmitting(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Fleet</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {total} aircraft registered
          </p>
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Aircraft
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <form onSubmit={handleSearch} className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search tail number, make, model..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </form>
        <div className="flex gap-2">
          {(['', 'active', 'in_maintenance', 'grounded'] as const).map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter(s)}
              className="whitespace-nowrap"
            >
              {s ? STATUS_CONFIG[s]?.label || s : 'All'}
            </Button>
          ))}
        </div>
      </div>

      {/* Aircraft Grid */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse border-border/50">
              <CardContent className="p-6"><div className="h-24 rounded bg-muted" /></CardContent>
            </Card>
          ))}
        </div>
      ) : aircraft.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
          <Plane className="h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium text-muted-foreground">No aircraft yet</p>
          <p className="text-sm text-muted-foreground">Add your first aircraft to get started.</p>
          <Button onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add Aircraft
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {aircraft.map((ac) => (
            <Link key={ac.id} to={`/fleet/${ac.id}`} className="block">
              <Card className="cursor-pointer border-border/50 transition-colors hover:border-brand-500/50 hover:bg-brand-500/5">
                <CardHeader className="flex flex-row items-start justify-between pb-2">
                  <div>
                    <CardTitle className="text-lg font-semibold">{ac.tail_number}</CardTitle>
                    <p className="text-sm text-muted-foreground">{ac.make} {ac.model} ({ac.year})</p>
                  </div>
                  <StatusBadge status={ac.status as AircraftStatus} />
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Base: </span>
                      <span>{ac.base}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Seats: </span>
                      <span>{ac.max_seats}</span>
                    </div>
                    {ac.total_airframe_hours != null && (
                      <div>
                        <span className="text-muted-foreground">Hours: </span>
                        <span>{ac.total_airframe_hours.toLocaleString()}</span>
                      </div>
                    )}
                    {ac.total_cycles != null && (
                      <div>
                        <span className="text-muted-foreground">Cycles: </span>
                        <span>{ac.total_cycles.toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Add Aircraft Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Aircraft</DialogTitle>
            <DialogDescription>Register a new aircraft in your fleet.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            {formError && (
              <div className="rounded-md bg-destructive/15 px-3 py-2 text-sm text-destructive">{formError}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Tail Number</label>
                <Input placeholder="C6-PRD" value={tailNumber} onChange={(e) => setTailNumber(e.target.value.toUpperCase())} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Base (ICAO)</label>
                <Input placeholder="MYNN" value={acBase} onChange={(e) => setAcBase(e.target.value.toUpperCase())} required />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Make</label>
                <Input placeholder="Cessna" value={acMake} onChange={(e) => setAcMake(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Model</label>
                <Input placeholder="208B" value={acModel} onChange={(e) => setAcModel(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Year</label>
                <Input type="number" value={acYear} onChange={(e) => setAcYear(e.target.value)} required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Seats</label>
                <Input type="number" min={1} value={acSeats} onChange={(e) => setAcSeats(e.target.value)} required />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Adding...' : 'Add Aircraft'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
