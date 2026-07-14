import { useState, useEffect, type FormEvent } from 'react'
import { Users, Plus, Search, Phone, Mail, MapPin, Award } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import api from '@/lib/api'

interface CrewMember {
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
  medical_expiry: string | null
  license_expiry: string | null
  base_airport: string | null
  last_90d_hours: number | null
  qualifications: any[]
}

const ROLE_COLORS: Record<string, string> = {
  captain: 'bg-blue-500/10 text-blue-500',
  first_officer: 'bg-cyan-500/10 text-cyan-500',
  sic: 'bg-indigo-500/10 text-indigo-500',
  mechanic: 'bg-amber-500/10 text-amber-500',
  flight_attendant: 'bg-pink-500/10 text-pink-500',
  dispatcher: 'bg-purple-500/10 text-purple-500',
}

export default function CrewPage() {
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)

  // Add form
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState('first_officer')
  const [licenseNum, setLicenseNum] = useState('')
  const [licenseExpiry, setLicenseExpiry] = useState('')
  const [medicalExpiry, setMedicalExpiry] = useState('')
  const [base, setBase] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchCrew = async (q = '') => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      const res = await api.get(`/api/v1/crew?${params}`)
      setCrew(res.data.data)
      setTotal(res.data.total)
    } catch { /* silent */ }
    setLoading(false)
  }

  useEffect(() => { fetchCrew() }, [])

  const handleSearch = (e: FormEvent) => { e.preventDefault(); fetchCrew(search) }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/v1/crew', {
        first_name: firstName, last_name: lastName,
        email: email || undefined, phone: phone || undefined,
        role, license_number: licenseNum || undefined,
        license_expiry: licenseExpiry || undefined,
        medical_expiry: medicalExpiry || undefined,
        base_airport: base || undefined,
      })
      setShowAdd(false)
      setFirstName(''); setLastName(''); setEmail(''); setPhone('')
      setLicenseNum(''); setLicenseExpiry(''); setMedicalExpiry(''); setBase('')
      await fetchCrew()
    } catch { /* silent */ }
    setSubmitting(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Crew</h1>
          <p className="mt-1 text-sm text-muted-foreground">{total} crew members</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Crew
        </Button>
      </div>

      <form onSubmit={handleSearch} className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search by name, email..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </form>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1,2,3].map((i) => (
            <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-24 rounded bg-muted" /></CardContent></Card>
          ))}
        </div>
      ) : crew.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
          <Users className="h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium text-muted-foreground">No crew yet</p>
          <Button onClick={() => setShowAdd(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add Crew Member
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {crew.map((c) => {
            const roleColor = ROLE_COLORS[c.role] || 'bg-muted text-muted-foreground'
            const isMedicalExpiring = c.medical_expiry && new Date(c.medical_expiry) < new Date(Date.now() + 30*86400000)
            return (
              <Card
                key={c.id}
                className="cursor-pointer border-border/50 transition-colors hover:border-brand-500/50 hover:bg-brand-500/5"
                onClick={() => window.location.href = `/crew/${c.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{c.display_name}</p>
                      <Badge variant="outline" className={`mt-1 ${roleColor}`}>
                        {c.role.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </div>
                    <Badge variant={c.status === 'active' ? 'default' : 'outline'} className={c.status !== 'active' ? 'text-muted-foreground' : ''}>
                      {c.status}
                    </Badge>
                  </div>
                  <div className="mt-3 space-y-1.5 text-sm text-muted-foreground">
                    {c.email && <p className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" /> {c.email}</p>}
                    {c.phone && <p className="flex items-center gap-1.5"><Phone className="h-3.5 w-3.5" /> {c.phone}</p>}
                    {c.base_airport && <p className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" /> {c.base_airport}</p>}
                    {c.license_number && <p className="flex items-center gap-1.5"><Award className="h-3.5 w-3.5" /> {c.license_number}</p>}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {c.license_expiry && (
                      <span className={`rounded-full px-2 py-0.5 ${new Date(c.license_expiry) < new Date() ? 'bg-red-500/10 text-red-500' : 'bg-muted'}`}>
                        Lic: {c.license_expiry}
                      </span>
                    )}
                    {c.medical_expiry && (
                      <span className={`rounded-full px-2 py-0.5 ${isMedicalExpiring ? 'bg-amber-500/10 text-amber-500' : 'bg-muted'}`}>
                        Med: {c.medical_expiry}
                      </span>
                    )}
                    {c.last_90d_hours != null && (
                      <span className="rounded-full bg-muted px-2 py-0.5">{c.last_90d_hours}h / 90d</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Crew Member</DialogTitle>
            <DialogDescription>Register a new crew member in your operation.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">First Name</label>
                <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Last Name</label>
                <Input value={lastName} onChange={(e) => setLastName(e.target.value)} required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Phone</label>
                <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="captain">Captain</option>
                  <option value="first_officer">First Officer</option>
                  <option value="sic">SIC</option>
                  <option value="mechanic">Mechanic</option>
                  <option value="dispatcher">Dispatcher</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Base (ICAO)</label>
                <Input placeholder="MYNN" value={base} onChange={(e) => setBase(e.target.value.toUpperCase())} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">License #</label>
                <Input value={licenseNum} onChange={(e) => setLicenseNum(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">License Expiry</label>
                <Input type="date" value={licenseExpiry} onChange={(e) => setLicenseExpiry(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Medical Expiry</label>
              <Input type="date" value={medicalExpiry} onChange={(e) => setMedicalExpiry(e.target.value)} />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Adding...' : 'Add Crew'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
