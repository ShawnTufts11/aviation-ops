import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plane, Wrench, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface Component {
  id: string
  name: string
  part_number: string
  serial_number: string
  component_type: string
  status: string
  life_limited: boolean
  tbo_hours: number | null
  installed_date: string | null
}

interface AircraftDetail {
  id: string
  tail_number: string
  make: string
  model: string
  year: number
  serial_number: string | null
  category: string
  status: string
  base: string
  home_airport: string
  country_reg: string
  mtow_kg: number | null
  max_seats: number
  max_cargo_kg: number | null
  total_airframe_hours: number | null
  total_cycles: number | null
  registration_expiry: string | null
  insurance_provider: string | null
  insurance_expiry: string | null
  created_at: string
}

export default function AircraftDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [aircraft, setAircraft] = useState<AircraftDetail | null>(null)
  const [components, setComponents] = useState<Component[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/aircraft/${id}`)
      .then((res) => {
        setAircraft(res.data.aircraft)
        setComponents(res.data.components)
      })
      .catch(() => navigate('/fleet'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!aircraft) return null

  const statusColor = aircraft.status === 'active' ? 'bg-green-500/10 text-green-500' :
    aircraft.status === 'in_maintenance' ? 'bg-amber-500/10 text-amber-500' :
    'bg-red-500/10 text-red-500'

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/fleet')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">{aircraft.tail_number}</h1>
            <Badge className={`${statusColor} border-current`} variant="outline">
              {aircraft.status.replace('_', ' ').toUpperCase()}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {aircraft.make} {aircraft.model} ({aircraft.year}) · {aircraft.serial_number || 'No S/N'}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview"><Plane className="mr-2 h-4 w-4" /> Overview</TabsTrigger>
          <TabsTrigger value="components"><Wrench className="mr-2 h-4 w-4" /> Components ({components.length})</TabsTrigger>
          <TabsTrigger value="documents"><FileText className="mr-2 h-4 w-4" /> Documents</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Identification</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Make</span><p className="font-medium">{aircraft.make}</p></div>
                <div><span className="text-muted-foreground">Model</span><p className="font-medium">{aircraft.model}</p></div>
                <div><span className="text-muted-foreground">Year</span><p className="font-medium">{aircraft.year}</p></div>
                <div><span className="text-muted-foreground">Serial #</span><p className="font-medium">{aircraft.serial_number || '—'}</p></div>
                <div><span className="text-muted-foreground">Category</span><p className="font-medium capitalize">{aircraft.category.replace(/_/g, ' ')}</p></div>
                <div><span className="text-muted-foreground">Country Reg</span><p className="font-medium">{aircraft.country_reg}</p></div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Operations</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Base</span><p className="font-medium">{aircraft.base}</p></div>
                <div><span className="text-muted-foreground">Home Airport</span><p className="font-medium">{aircraft.home_airport}</p></div>
                <div><span className="text-muted-foreground">Max Seats</span><p className="font-medium">{aircraft.max_seats}</p></div>
                <div><span className="text-muted-foreground">Max Cargo</span><p className="font-medium">{aircraft.max_cargo_kg ? `${aircraft.max_cargo_kg} kg` : '—'}</p></div>
                <div><span className="text-muted-foreground">MTOW</span><p className="font-medium">{aircraft.mtow_kg ? `${aircraft.mtow_kg} kg` : '—'}</p></div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Usage</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Airframe Hours</span><p className="font-medium">{aircraft.total_airframe_hours?.toLocaleString() ?? '—'}</p></div>
                <div><span className="text-muted-foreground">Total Cycles</span><p className="font-medium">{aircraft.total_cycles?.toLocaleString() ?? '—'}</p></div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Compliance</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Registration Exp</span><p className="font-medium">{aircraft.registration_expiry || '—'}</p></div>
                <div><span className="text-muted-foreground">Insurance</span><p className="font-medium">{aircraft.insurance_provider || '—'}</p></div>
                <div><span className="text-muted-foreground">Insurance Exp</span><p className="font-medium">{aircraft.insurance_expiry || '—'}</p></div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Components Tab */}
        <TabsContent value="components">
          {components.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12">
              <Wrench className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No tracked components</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Part #</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Serial #</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">TBO Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {components.map((c) => (
                    <tr key={c.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-3 font-medium">{c.name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{c.part_number}</td>
                      <td className="px-4 py-3 text-muted-foreground">{c.serial_number}</td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">{c.component_type}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          c.status === 'serviceable' ? 'bg-green-500/10 text-green-500' :
                          c.status === 'overhaul_due' ? 'bg-amber-500/10 text-amber-500' :
                          'bg-muted text-muted-foreground'
                        }`}>
                          {c.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{c.tbo_hours ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        {/* Documents Tab — placeholder */}
        <TabsContent value="documents">
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12">
            <FileText className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Documents coming in Module 6 (Compliance)</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
