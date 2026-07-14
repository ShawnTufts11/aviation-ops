import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Award, Phone, Mail, MapPin, Wrench, Plane } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface Qualification {
  id: string
  qual_type: string
  status: string
  aircraft_type: string | null
  issued_date: string | null
  expiry_date: string | null
}

interface CrewDetail {
  id: string
  first_name: string
  last_name: string
  display_name: string
  email: string | null
  phone: string | null
  role: string
  status: string
  license_type: string | null
  license_number: string | null
  license_country: string | null
  license_expiry: string | null
  medical_class: string | null
  medical_expiry: string | null
  base_airport: string | null
  last_90d_hours: number | null
  last_12m_hours: number | null
  qualifications: Qualification[]
}

const AUTHORIZATION_MATRIX: Record<string, string[]> = {
  captain: ['Sign off maintenance', 'Release aircraft to service', 'Approve flight releases', 'Authorize repairs', 'Conduct pre-flight'],
  first_officer: ['Sign off maintenance', 'Conduct pre-flight'],
  sic: ['Conduct pre-flight'],
  mechanic: ['Sign off maintenance', 'Release aircraft to service', 'Authorize repairs', 'Conduct inspections'],
  dispatcher: ['Schedule flights', 'File flight plans', 'Coordinate crew'],
  super_admin: ['All actions'],
}

const QUAL_LABELS: Record<string, string> = {
  type_rating: 'Type Rating',
  proficiency_check: 'Proficiency Check',
  line_check: 'Line Check',
  instrument_rating: 'Instrument Rating',
  recurrent_training: 'Recurrent Training',
  hazmat: 'Hazmat Certified',
  dgr: 'Dangerous Goods',
  first_aid: 'First Aid',
}

export default function CrewDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [crew, setCrew] = useState<CrewDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/crew/${id}`)
      .then((res) => setCrew(res.data))
      .catch(() => navigate('/crew'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!crew) return null

  const authorizations = AUTHORIZATION_MATRIX[crew.role] || []
  const isMedicalExpiring = crew.medical_expiry && new Date(crew.medical_expiry) < new Date(Date.now() + 30*86400000)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/crew')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{crew.display_name}</h1>
            <Badge variant={crew.status === 'active' ? 'default' : 'outline'}>{crew.status}</Badge>
          </div>
          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline" className="capitalize">{crew.role.replace('_', ' ')}</Badge>
            {crew.base_airport && <><MapPin className="h-3.5 w-3.5" />{crew.base_airport}</>}
          </p>
        </div>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile"><Award className="mr-2 h-4 w-4" /> Profile</TabsTrigger>
          <TabsTrigger value="authorization"><Wrench className="mr-2 h-4 w-4" /> Authorization</TabsTrigger>
          <TabsTrigger value="qualifications"><Plane className="mr-2 h-4 w-4" /> Qualifications ({crew.qualifications.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Contact</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {crew.email && <p className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" />{crew.email}</p>}
                {crew.phone && <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-muted-foreground" />{crew.phone}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Licenses & Medical</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p><span className="text-muted-foreground">License: </span>{crew.license_number || '—'}</p>
                <p><span className="text-muted-foreground">Expiry: </span>
                  <span className={crew.license_expiry && new Date(crew.license_expiry) < new Date() ? 'text-red-500' : ''}>
                    {crew.license_expiry || '—'}
                  </span>
                </p>
                <p><span className="text-muted-foreground">Medical: </span>
                  <span className={isMedicalExpiring ? 'text-amber-500' : ''}>
                    {crew.medical_expiry || '—'}
                  </span>
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Currency</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p><span className="text-muted-foreground">Last 90 days: </span>{crew.last_90d_hours ?? '0'} hrs</p>
                <p><span className="text-muted-foreground">Last 12 months: </span>{crew.last_12m_hours ?? '0'} hrs</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="authorization">
          <Card>
            <CardHeader><CardTitle className="text-base">Authorized Actions — {crew.role.replace('_', ' ').toUpperCase()}</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                {authorizations.map((action) => (
                  <div key={action} className="flex items-center gap-3 rounded-md border border-border/50 p-3 text-sm">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500/10 text-green-500">
                      <Award className="h-3.5 w-3.5" />
                    </span>
                    <span>{action}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="qualifications">
          {crew.qualifications.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12">
              <Award className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No qualifications recorded</p>
            </div>
          ) : (
            <div className="space-y-3">
              {crew.qualifications.map((q) => (
                <Card key={q.id} className="border-border/50">
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <p className="font-medium">{QUAL_LABELS[q.qual_type] || q.qual_type.replace(/_/g, ' ')}</p>
                      {q.aircraft_type && <p className="text-sm text-muted-foreground">{q.aircraft_type}</p>}
                    </div>
                    <Badge variant={q.status === 'current' ? 'default' : 'outline'} className={q.status === 'expired' ? 'text-red-500' : q.status === 'expiring_soon' ? 'text-amber-500' : ''}>
                      {q.status.replace('_', ' ')}
                    </Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
