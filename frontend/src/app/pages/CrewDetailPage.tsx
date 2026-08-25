import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Award, Phone, Mail, MapPin, Wrench, Plane, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import api from '@/lib/api'
import { useAuthContext } from '@/features/auth/AuthContext'

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

const QUAL_TYPES = [
  'type_rating', 'proficiency_check', 'line_check', 'instrument_rating',
  'recurrent_training', 'hazmat', 'dgr', 'first_aid',
]

function daysUntil(d: string): number {
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}

function qualBorder(d: string | null): string {
  if (!d) return 'border-border/50'
  const days = daysUntil(d)
  if (days < 30) return 'border-red-500/30'
  if (days < 90) return 'border-amber-500/30'
  return 'border-green-500/20'
}

function qualBadge(d: string | null): { text: string; cls: string } {
  if (!d) return { text: 'No expiry', cls: 'bg-muted text-muted-foreground' }
  const days = daysUntil(d)
  if (days < 0) return { text: 'EXPIRED', cls: 'bg-red-500/10 text-red-500' }
  if (days < 30) return { text: `${days}d left`, cls: 'bg-red-500/10 text-red-500' }
  if (days < 90) return { text: `${days}d left`, cls: 'bg-amber-500/10 text-amber-500' }
  return { text: `${days}d left`, cls: 'bg-green-500/10 text-green-500' }
}

export default function CrewDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [crew, setCrew] = useState<CrewDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const { user } = useAuthContext()
  const canEdit = user?.role === 'super_admin' || user?.role === 'ops_manager'

  // Add qual dialog
  const [showAdd, setShowAdd] = useState(false)
  const [qualType, setQualType] = useState('type_rating')
  const [qualAcft, setQualAcft] = useState('')
  const [qualIssued, setQualIssued] = useState('')
  const [qualExpiry, setQualExpiry] = useState('')
  const [qualBusy, setQualBusy] = useState(false)

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/crew/${id}`)
      .then((res) => setCrew(res.data))
      .catch(() => navigate('/crew'))
      .finally(() => setLoading(false))
  }, [id])

  const handleAddQual = async () => {
    setQualBusy(true)
    try {
      await api.post(`/api/v1/crew/${crew!.id}/qualifications`, {
        qual_type: qualType,
        aircraft_type: qualAcft || undefined,
        issued_date: qualIssued || undefined,
        expiry_date: qualExpiry || undefined,
      })
      setShowAdd(false)
      setQualType('type_rating'); setQualAcft(''); setQualIssued(''); setQualExpiry('')
      const res = await api.get(`/api/v1/crew/${id}`)
      setCrew(res.data)
    } catch { /* silent */ }
    setQualBusy(false)
  }

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!crew) return null

  const authorizations = AUTHORIZATION_MATRIX[crew.role] || []
  const isMedicalExpiring = crew.medical_expiry && new Date(crew.medical_expiry) < new Date(Date.now() + 30 * 86400000)

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
                {crew.license_expiry && (
                  <p><span className="text-muted-foreground">License Expiry: </span>
                    <span className={new Date(crew.license_expiry) < new Date() ? 'font-medium text-red-500' : ''}>
                      {new Date(crew.license_expiry).toLocaleDateString()} {new Date(crew.license_expiry) < new Date() ? '(EXPIRED)' : `(${daysUntil(crew.license_expiry)}d)`}
                    </span>
                  </p>
                )}
                <p><span className="text-muted-foreground">Medical: </span>
                  <span className={isMedicalExpiring ? 'font-medium text-amber-500' : ''}>
                    {crew.medical_expiry ? `${new Date(crew.medical_expiry).toLocaleDateString()} (${daysUntil(crew.medical_expiry)}d)` : '—'}
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
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">{crew.qualifications.length} qualification{crew.qualifications.length !== 1 ? 's' : ''}</p>
              {canEdit && (
                <Button size="sm" variant="outline" onClick={() => setShowAdd(true)}>
                  <Plus className="mr-1.5 h-3.5 w-3.5" /> Add
                </Button>
              )}
            </div>
            {crew.qualifications.length === 0 ? (
              <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12">
                <Award className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No qualifications recorded</p>
              </div>
            ) : (
              <div className="space-y-2">
                {crew.qualifications.map((q) => {
                  const badge = qualBadge(q.expiry_date)
                  return (
                    <Card key={q.id} className={`border ${qualBorder(q.expiry_date)}`}>
                      <CardContent className="flex items-center justify-between p-3">
                        <div className="flex items-center gap-3">
                          <span className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${badge.cls}`}>
                            <Award className="h-4 w-4" />
                          </span>
                          <div>
                            <p className="text-sm font-medium">{QUAL_LABELS[q.qual_type] || q.qual_type.replace(/_/g, ' ')}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              {q.aircraft_type && <span>{q.aircraft_type}</span>}
                              {q.issued_date && <span>Issued {new Date(q.issued_date).toLocaleDateString()}</span>}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant="outline" className={badge.cls}>{badge.text}</Badge>
                          {q.expiry_date && (
                            <p className="mt-0.5 text-[10px] text-muted-foreground">{new Date(q.expiry_date).toLocaleDateString()}</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}
          </div>

          <Dialog open={showAdd} onOpenChange={setShowAdd}>
            <DialogContent className="sm:max-w-sm">
              <DialogHeader><DialogTitle>Add Qualification</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Type</label>
                  <select className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={qualType} onChange={(e) => setQualType(e.target.value)}>
                    {QUAL_TYPES.map((t) => (
                      <option key={t} value={t}>{QUAL_LABELS[t] || t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Aircraft Type</label>
                  <Input placeholder="BT67, K35X, K200, T300" value={qualAcft} onChange={(e) => setQualAcft(e.target.value.toUpperCase())} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Issued</label>
                    <Input type="date" value={qualIssued} onChange={(e) => setQualIssued(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Expiry</label>
                    <Input type="date" value={qualExpiry} onChange={(e) => setQualExpiry(e.target.value)} />
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleAddQual} disabled={qualBusy}>{qualBusy ? 'Adding...' : 'Add'}</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>
    </div>
  )
}
