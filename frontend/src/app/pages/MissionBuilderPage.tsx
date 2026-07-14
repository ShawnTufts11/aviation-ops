import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, X, ArrowLeft, Plane, MapPin, Users, Search, FileWarning } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import api from '@/lib/api'

interface Aircraft { id: string; tail_number: string }
interface LegForm { leg_number: number; departure: string; arrival: string; distance: string }
interface PaxForm { name: string; nationality: string; weight: string }

export default function MissionBuilderPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [acId, setAcId] = useState('')
  const [homeBase] = useState('MYNN')
  const [legs, setLegs] = useState<LegForm[]>([
    { leg_number: 1, departure: 'MYNN', arrival: '', distance: '' }
  ])
  const [passengers, setPassengers] = useState<PaxForm[]>([])
  const [paxSearch, setPaxSearch] = useState('')
  const [paxResults, setPaxResults] = useState<any[]>([])
  const [missionId, setMissionId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [warnings, setWarnings] = useState<string[]>([])

  useEffect(() => {
    api.get('/api/v1/aircraft?per_page=100').then((r) => setAircraft(r.data.data))
  }, [])

  const updateLeg = (idx: number, field: string, value: string) => {
    const updated = legs.map((leg, i) => {
      if (i !== idx) return leg
      const newLeg = { ...leg, [field]: value }
      // Auto-fill departure for leg 2+ from previous arrival
      if (field === 'arrival' && idx < legs.length - 1) {
        return newLeg
      }
      return newLeg
    })
    setLegs(updated)
  }

  const addLeg = () => {
    const last = legs[legs.length - 1]
    setLegs([...legs, {
      leg_number: legs.length + 1,
      departure: last.arrival || '',
      arrival: '',
      distance: '',
    }])
  }

  const removeLeg = (idx: number) => {
    if (legs.length <= 1) return
    const updated = legs.filter((_, i) => i !== idx).map((l, i) => ({ ...l, leg_number: i + 1 }))
    setLegs(updated)
  }

  const addPassenger = () => setPassengers([...passengers, { name: '', nationality: 'US', weight: '80' }])
  const updatePax = (idx: number, field: string, value: string) => {
    setPassengers(passengers.map((p, i) => i === idx ? { ...p, [field]: value } : p))
  }
  const removePax = (idx: number) => setPassengers(passengers.filter((_, i) => i !== idx))

  const handleCreate = async () => {
    setSubmitting(true)
    try {
      // Create mission
      const m = await api.post('/api/v1/missions', {
        aircraft_id: acId || undefined,
        home_base: homeBase,
      })
      const mid = m.data.id
      setMissionId(mid)

      // Add legs
      for (const leg of legs) {
        const l = await api.post(`/api/v1/missions/${mid}/legs`, {
          leg_number: leg.leg_number,
          departure_airport: leg.departure,
          arrival_airport: leg.arrival,
          distance_nm: leg.distance ? parseInt(leg.distance) : undefined,
        })

        // Add passengers to each leg
        for (const pax of passengers) {
          await api.post(`/api/v1/missions/${mid}/legs/${l.data.id}/manifest`, {
            full_name: pax.name,
            nationality: pax.nationality,
            weight_kg: pax.weight ? parseFloat(pax.weight) : undefined,
            entry_type: 'passenger',
            boarding_leg_number: leg.leg_number,
          })
        }
      }

      // Get warnings
      const detail = await api.get(`/api/v1/missions/${mid}`)
      setWarnings(detail.data.warnings || [])
      setStep(4)
    } catch { /* silent */ }
    setSubmitting(false)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/missions')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New Mission</h1>
          <p className="text-sm text-muted-foreground">Step {step} of 4</p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex gap-1">
        {[1,2,3,4].map((s) => (
          <div key={s} className={`h-1.5 flex-1 rounded-full ${s <= step ? 'bg-brand-500' : 'bg-muted'}`} />
        ))}
      </div>

      {/* Step 1: Aircraft */}
      {step === 1 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Plane className="h-5 w-5 text-brand-400" /> Select Aircraft
            </h2>
            <div className="space-y-2">
              <label className="text-sm font-medium">Aircraft</label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={acId} onChange={(e) => setAcId(e.target.value)}>
                <option value="">Select aircraft...</option>
                {aircraft.map((a) => (
                  <option key={a.id} value={a.id}>{a.tail_number}</option>
                ))}
              </select>
            </div>
            <p className="text-xs text-muted-foreground">Home base: {homeBase}</p>
            <div className="flex justify-end">
              <Button onClick={() => setStep(2)} disabled={!acId}>Next: Routes</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Legs */}
      {step === 2 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <MapPin className="h-5 w-5 text-brand-400" /> Flight Legs
            </h2>
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
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-xs text-muted-foreground">From</label>
                      <Input value={leg.departure} onChange={(e) => updateLeg(i, 'departure', e.target.value.toUpperCase())}
                        placeholder="MYNN" disabled={i > 0} className={i > 0 ? 'opacity-60' : ''} />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">To</label>
                      <Input value={leg.arrival} onChange={(e) => {
                        updateLeg(i, 'arrival', e.target.value.toUpperCase())
                        // Auto-fill next leg departure
                        if (i < legs.length - 1) {
                          const updated = [...legs]
                          updated[i + 1] = { ...updated[i + 1], departure: e.target.value.toUpperCase() }
                          setLegs(updated)
                        }
                      }} placeholder="MTPP" />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Distance (nm)</label>
                      <Input type="number" value={leg.distance} onChange={(e) => updateLeg(i, 'distance', e.target.value)} placeholder="530" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" size="sm" onClick={addLeg} className="w-full">
              <Plus className="mr-2 h-4 w-4" /> Add Leg
            </Button>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={() => setStep(3)}>Next: Passengers</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Passengers */}
      {step === 3 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Users className="h-5 w-5 text-brand-400" /> Passengers & Cargo
            </h2>

            {/* Search existing passengers */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search existing passengers by name or passport..."
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
                        // Check if already added
                        if (!passengers.find(p => p.name === r.full_name)) {
                          setPassengers([...passengers, {
                            name: r.full_name,
                            nationality: r.nationality || '',
                            weight: r.weight_kg?.toString() || '',
                          }])
                        }
                        setPaxSearch('')
                        setPaxResults([])
                      }}>
                      <span className="font-medium">{r.full_name}</span>
                      <span className="text-xs text-muted-foreground">{r.nationality} {r.passport_number ? `· ${r.passport_number}` : ''}</span>
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
            <Button variant="outline" size="sm" onClick={addPassenger}>
              <Plus className="mr-2 h-4 w-4" /> Add Manually
            </Button>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
              <Button onClick={handleCreate} disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Mission'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Review */}
      {step === 4 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-green-500">
              <Plane className="h-5 w-5" /> Mission Created
            </h2>
            {warnings.length > 0 && (
              <div className="space-y-2">
                <p className="flex items-center gap-2 text-sm font-medium text-amber-500">
                  <FileWarning className="h-4 w-4" /> Pre-flight Warnings
                </p>
                {warnings.map((w, i) => (
                  <div key={i} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2 text-sm text-amber-500">
                    {w}
                  </div>
                ))}
              </div>
            )}
            {warnings.length === 0 && (
              <p className="text-sm text-green-500">No warnings — all checks passed.</p>
            )}
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => navigate(`/missions/${missionId}`)}>
                View Mission
              </Button>
              <Button onClick={() => navigate('/missions')}>
                Back to Missions
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
