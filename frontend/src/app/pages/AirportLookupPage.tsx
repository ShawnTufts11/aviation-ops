import { useState, useEffect, useCallback } from 'react'
import { Search, Plane, MapPin, Sun, Moon, Fuel, Shield, Ruler, Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import { AcronymSpan } from '@/components/ui/acronym'
import api from '@/lib/api'

interface Airport {
  icao_code: string
  iata_code: string | null
  name: string
  city: string | null
  country_code: string
  longest_runway_ft: number | null
  runway_surface: string | null
  has_night_ops: boolean
  has_jet_a: boolean
  has_avgas: boolean
  has_customs: boolean
  elevation_ft: number | null
  latitude: number
  longitude: number
  timezone?: string
  fuel_price_jet_a_usd?: number | null
  fuel_price_avgas_usd?: number | null
  customs_hours?: string | null
  payment_type?: string | null
  landing_fee_usd?: number | null
  overnight_parking_usd?: number | null
  handling_fee_usd?: number | null
  customs_fee_usd?: number | null
}

const SURFACE_OPTIONS = ['asphalt', 'concrete', 'grass', 'gravel', 'water']
const RUNWAY_PRESETS = [
  { label: 'Any', value: 0 },
  { label: '2,000ft+', value: 2000 },
  { label: '3,000ft+', value: 3000 },
  { label: '4,000ft+', value: 4000 },
  { label: '5,000ft+', value: 5000 },
  { label: '6,000ft+', value: 6000 },
]

export default function AirportLookupPage() {
  const [airports, setAirports] = useState<Airport[]>([])
  const [total, setTotal] = useState(0)
  const [selectedAirport, setSelectedAirport] = useState<Airport | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [minRunway, setMinRunway] = useState(0)
  const [nightOps, setNightOps] = useState<boolean | null>(null)
  const [customs, setCustoms] = useState<boolean | null>(null)
  const [jetA, setJetA] = useState<boolean | null>(null)
  const [surface, setSurface] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [lookupIcao, setLookupIcao] = useState('')
  const [lookupResult, setLookupResult] = useState<any | null>(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState('')
  const [addingAirport, setAddingAirport] = useState(false)

  const fetchAirports = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('q', search)
      if (country) params.set('country', country.toUpperCase())
      if (minRunway > 0) params.set('min_rwy', String(minRunway))
      if (nightOps !== null) params.set('has_night_ops', String(nightOps))
      if (customs !== null) params.set('has_customs', String(customs))
      if (jetA !== null) params.set('has_jet_a', String(jetA))
      if (surface) params.set('surface', surface)
      const res = await api.get(`/api/v1/airports?${params}`)
      setAirports(res.data.data)
      setTotal(res.data.total)
    } catch { /* silent */ }
    setLoading(false)
  }, [search, country, minRunway, nightOps, customs, jetA, surface])

  useEffect(() => { fetchAirports() }, [fetchAirports])

  const handleLookup = async () => {
    if (!lookupIcao || lookupIcao.length < 3) return
    setLookupLoading(true)
    setLookupError('')
    setLookupResult(null)
    try {
      const res = await api.get(`/api/v1/airports/lookup/${lookupIcao}`)
      setLookupResult(res.data)
    } catch (err: any) {
      setLookupError(err?.response?.data?.detail || 'Lookup failed')
    }
    setLookupLoading(false)
  }

  const handleAddAirport = async () => {
    if (!lookupResult?.airport) return
    setAddingAirport(true)
    try {
      await api.post('/api/v1/airports', {
        icao_code: lookupResult.airport.icao_code,
        name: lookupResult.airport.name,
        city: lookupResult.airport.city || undefined,
        latitude: lookupResult.airport.latitude,
        longitude: lookupResult.airport.longitude,
        timezone: lookupResult.airport.timezone || 'UTC',
        country_code: lookupResult.airport.country_code,
        elevation_ft: lookupResult.airport.elevation_ft || undefined,
        iata_code: lookupResult.airport.iata_code || undefined,
      })
      setLookupResult(null)
      setLookupIcao('')
      fetchAirports()
    } catch { /* silent */ }
    setAddingAirport(false)
  }

  const runwayClass = (ft: number | null) => {
    if (!ft) return 'text-muted-foreground'
    if (ft < 3000) return 'text-red-500'
    if (ft < 4000) return 'text-amber-500'
    if (ft < 6000) return 'text-green-500'
    return 'text-green-400'
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight"><AcronymSpan text="ICAO" /> Lookup</h1>
          <p className="mt-1 text-sm text-muted-foreground">{total} airports in database</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
          {showFilters ? 'Hide Filters' : 'Filters'}
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-9" placeholder="Search by ICAO, airport name, city..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {/* Filters */}
      {showFilters && (
        <Card>
          <CardContent className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><MapPin className="h-3 w-3" /> Country</label>
              <Input placeholder="BS, HT, US..." value={country} onChange={(e) => setCountry(e.target.value.toUpperCase())} maxLength={2} className="h-8 text-sm" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><Ruler className="h-3 w-3" /> Min Runway</label>
              <div className="flex flex-wrap gap-1">
                {RUNWAY_PRESETS.map((p) => (
                  <button key={p.value} onClick={() => setMinRunway(minRunway === p.value ? 0 : p.value)}
                    className={`px-2 py-0.5 rounded text-xs border ${minRunway === p.value ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><MapPin className="h-3 w-3" /> Surface</label>
              <div className="flex flex-wrap gap-1">
                <button onClick={() => setSurface(surface === '' ? 'paved' : '')}
                  className={`px-2 py-0.5 rounded text-xs border ${surface === 'paved' ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                  Paved only
                </button>
                {SURFACE_OPTIONS.map((s) => (
                  <button key={s} onClick={() => setSurface(surface === s ? '' : s)}
                    className={`px-2 py-0.5 rounded text-xs border capitalize ${surface === s ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><Sun className="h-3 w-3" /> Night Ops</label>
              <div className="flex gap-1">
                {[
                  { label: 'Any', value: null },
                  { label: 'Yes', value: true },
                  { label: 'No', value: false },
                ].map((opt) => (
                  <button key={String(opt.value)} onClick={() => setNightOps(opt.value)}
                    className={`px-2 py-0.5 rounded text-xs border ${nightOps === opt.value ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><Fuel className="h-3 w-3" /> Fuel</label>
              <div className="flex gap-1">
                {[
                  { label: 'Any', value: null },
                  { label: 'Jet-A', value: true },
                  { label: 'No Jet-A', value: false },
                ].map((opt) => (
                  <button key={String(opt.value)} onClick={() => setJetA(opt.value)}
                    className={`px-2 py-0.5 rounded text-xs border ${jetA === opt.value ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium flex items-center gap-1"><Shield className="h-3 w-3" /> Customs</label>
              <div className="flex gap-1">
                {[
                  { label: 'Any', value: null },
                  { label: 'Yes', value: true },
                  { label: 'No', value: false },
                ].map((opt) => (
                  <button key={String(opt.value)} onClick={() => setCustoms(opt.value)}
                    className={`px-2 py-0.5 rounded text-xs border ${customs === opt.value ? 'bg-brand-500/10 text-brand-500 border-brand-500/30' : 'border-border/50 text-muted-foreground hover:border-brand-500/30'}`}>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1,2,3,4,5,6].map((i) => (
            <Card key={i} className="animate-pulse"><CardContent className="p-4"><div className="h-20 rounded bg-muted" /></CardContent></Card>
          ))}
        </div>
      ) : airports.length === 0 && !lookupResult ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-12">
          <MapPin className="h-10 w-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No airports in your database match</p>
          <div className="flex gap-2">
            <Input className="w-40" placeholder="Lookup ICAO..." value={lookupIcao}
              onChange={(e) => setLookupIcao(e.target.value.toUpperCase())} maxLength={4}
              onKeyDown={(e) => e.key === 'Enter' && handleLookup()} />
            <Button size="sm" variant="outline" onClick={handleLookup} disabled={lookupLoading}>
              {lookupLoading ? 'Searching...' : 'Lookup'}
            </Button>
          </div>
          {lookupError && <p className="text-xs text-red-500">{lookupError}</p>}
        </div>
      ) : airports.length === 0 && lookupResult ? (
        <Card className="border-brand-500/30">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-lg">{lookupResult.airport.icao_code}</p>
                {lookupResult.airport.iata_code && <p className="text-xs text-muted-foreground">{lookupResult.airport.iata_code}</p>}
              </div>
              <Badge>{lookupResult.in_db ? 'In Database' : 'New'}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {lookupResult.airport.name}{lookupResult.airport.city ? `, ${lookupResult.airport.city}` : ''}
              <span className="ml-2 text-xs">({lookupResult.airport.country_code})</span>
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {lookupResult.airport.elevation_ft && (
                <span className="inline-flex items-center gap-0.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px]">
                  <Plane className="h-2.5 w-2.5" />{lookupResult.airport.elevation_ft}ft
                </span>
              )}
            </div>
            {!lookupResult.in_db && (
              <div className="mt-3 flex items-center gap-2 border-t border-border/50 pt-3">
                <Button size="sm" onClick={handleAddAirport} disabled={addingAirport}>
                  {addingAirport ? 'Adding...' : 'Add to Database'}
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setLookupResult(null); setLookupIcao('') }}>
                  Cancel
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {airports.map((a) => (
            <Card key={a.icao_code} className="border-border/50 hover:border-brand-500/40 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-base cursor-pointer hover:text-brand-400 transition-colors"
                       onClick={() => setSelectedAirport(a)}>
                      {a.icao_code}</p>
                    {a.iata_code && <p className="text-xs text-muted-foreground">{a.iata_code}</p>}
                  </div>
                  <Badge variant="outline">{a.country_code}</Badge>
                </div>
                <p className="mt-1 text-sm leading-tight text-muted-foreground line-clamp-2">{a.name}{a.city ? `, ${a.city}` : ''}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {a.longest_runway_ft && (
                    <span className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${runwayClass(a.longest_runway_ft)} bg-current/5`}>
                      <Ruler className="h-2.5 w-2.5" />{a.longest_runway_ft}ft
                    </span>
                  )}
                  {a.runway_surface && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {a.runway_surface}
                    </span>
                  )}
                  {a.has_night_ops && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-500">
                      <Moon className="h-2.5 w-2.5" />Night
                    </span>
                  )}
                  {a.has_jet_a && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-green-500/10 px-1.5 py-0.5 text-[10px] text-green-500">
                      <Fuel className="h-2.5 w-2.5" />Jet-A
                    </span>
                  )}
                  {a.has_customs && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500">
                      <Shield className="h-2.5 w-2.5" />Customs
                    </span>
                  )}
                  {a.elevation_ft && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      <Plane className="h-2.5 w-2.5" />{a.elevation_ft}ft
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Airport Detail Dialog */}
      <Dialog open={!!selectedAirport} onOpenChange={(o) => !o && setSelectedAirport(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-brand-400" />
              {selectedAirport?.icao_code}
              {selectedAirport?.iata_code && <span className="text-muted-foreground font-normal">· {selectedAirport.iata_code}</span>}
            </DialogTitle>
            <DialogDescription>
              {selectedAirport?.name}{selectedAirport?.city ? `, ${selectedAirport.city}` : ''}
            </DialogDescription>
          </DialogHeader>
          {selectedAirport && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Runway & Ops</p>
                <p><span className="text-muted-foreground">Runway:</span> {selectedAirport.longest_runway_ft ? `${selectedAirport.longest_runway_ft}ft` : 'N/A'} {selectedAirport.runway_surface && `· ${selectedAirport.runway_surface}`}</p>
                <p><span className="text-muted-foreground">Elevation:</span> {selectedAirport.elevation_ft ?? 'N/A'}ft</p>
                <p><span className="text-muted-foreground">Night Ops:</span> {selectedAirport.has_night_ops ? '✅ Yes' : '❌ No'}</p>
                <p><span className="text-muted-foreground">Location:</span> {selectedAirport.latitude?.toFixed(3)}, {selectedAirport.longitude?.toFixed(3)}</p>
                <p><span className="text-muted-foreground">Timezone:</span> {selectedAirport.timezone || 'UTC'}</p>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Fuel & Services</p>
                <p><span className="text-muted-foreground">Jet-A:</span> {selectedAirport.has_jet_a ? `✅ ($${selectedAirport.fuel_price_jet_a_usd?.toFixed(2) ?? '?'}/gal)` : '❌'}</p>
                <p><span className="text-muted-foreground">Avgas:</span> {selectedAirport.has_avgas ? `✅ ($${selectedAirport.fuel_price_avgas_usd?.toFixed(2) ?? '?'}/gal)` : '❌'}</p>
                <p><span className="text-muted-foreground">Customs:</span> {selectedAirport.has_customs ? `✅ ${selectedAirport.customs_hours || ''}` : '❌'}</p>
                <p><span className="text-muted-foreground">Payment:</span> {selectedAirport.payment_type === 'cash_only' ? '⚠ Cash only' : selectedAirport.payment_type || 'Mixed'}</p>
              </div>
              <div className="col-span-2 border-t pt-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Estimated Fees</p>
                <div className="grid grid-cols-2 gap-1 text-xs">
                  <span>Landing: <strong>${selectedAirport.landing_fee_usd?.toFixed(2) ?? '—'}</strong></span>
                  <span>Parking: <strong>${selectedAirport.overnight_parking_usd?.toFixed(2) ?? '—'}/night</strong></span>
                  <span>Handling: <strong>${selectedAirport.handling_fee_usd?.toFixed(2) ?? '—'}</strong></span>
                  <span>Customs: <strong>${selectedAirport.customs_fee_usd?.toFixed(2) ?? '—'}</strong></span>
                </div>
              </div>
              <div className="col-span-2 border-t pt-2 flex justify-between items-center">
                <a
                  href={`https://www.airnav.com/airport/${selectedAirport.icao_code}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-brand-400 hover:underline flex items-center gap-1"
                >
                  <Globe className="h-3 w-3" /> View on AirNav
                </a>
                <a
                  href={`https://www.aviationweather.gov/metar/data?ids=${selectedAirport.icao_code}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-brand-400 hover:underline flex items-center gap-1"
                >
                  <Sun className="h-3 w-3" /> Weather Brief
                </a>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
