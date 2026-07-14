import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, Plus, Search, Phone, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import api from '@/lib/api'

interface Passenger {
  id: string
  full_name: string
  nationality: string | null
  passport_number: string | null
  email: string | null
  phone: string | null
  total_flights: number
  last_flight: string | null
}

export default function PassengersPage() {
  const [passengers, setPassengers] = useState<Passenger[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const navigate = useNavigate()

  // Add form
  const [name, setName] = useState('')
  const [nationality, setNationality] = useState('')
  const [passport, setPassport] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [weight, setWeight] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchPassengers = async (q = '') => {
    const params = q ? `?q=${encodeURIComponent(q)}` : ''
    try {
      const res = await api.get(`/api/v1/passengers${params}`)
      setPassengers(res.data.data)
      setTotal(res.data.total)
    } catch { /* silent */ }
  }

  useEffect(() => { fetchPassengers() }, [])

  const handleSearch = (e: FormEvent) => { e.preventDefault(); fetchPassengers(search) }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/v1/passengers', {
        full_name: name,
        nationality: nationality || undefined,
        passport_number: passport || undefined,
        email: email || undefined,
        phone: phone || undefined,
        weight_kg: weight ? parseFloat(weight) : undefined,
      })
      setShowAdd(false)
      setName(''); setNationality(''); setPassport(''); setEmail(''); setPhone(''); setWeight('')
      await fetchPassengers()
    } catch { /* silent */ }
    setSubmitting(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Passengers</h1>
          <p className="mt-1 text-sm text-muted-foreground">{total} profiles</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Passenger
        </Button>
      </div>

      <form onSubmit={handleSearch} className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search by name, passport, or nationality..." value={search}
          onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </form>

      {passengers.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
          <Users className="h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium text-muted-foreground">No passengers yet</p>
          <p className="text-sm text-muted-foreground">Add passengers or they'll be auto-created when you add them to a mission.</p>
          <Button onClick={() => setShowAdd(true)}><Plus className="mr-2 h-4 w-4" /> Add Passenger</Button>
        </div>
      ) : (
        <div className="space-y-3">
          {passengers.map((p) => (
            <Card key={p.id} className="cursor-pointer border-border/50 transition-colors hover:border-brand-500/50"
              onClick={() => navigate(`/passengers/${p.id}`)}>
              <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{p.full_name}</span>
                    {p.nationality && <Badge variant="outline">{p.nationality}</Badge>}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    {p.passport_number && <span className="font-mono text-xs">{p.passport_number}</span>}
                    {p.email && <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{p.email}</span>}
                    {p.phone && <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{p.phone}</span>}
                    <span>{p.total_flights} flight{p.total_flights !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Passenger</DialogTitle>
            <DialogDescription>Create a passenger profile for faster manifest entry.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Full Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Nationality</label>
                <Input placeholder="US" value={nationality} onChange={(e) => setNationality(e.target.value.toUpperCase())} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Weight (kg)</label>
                <Input type="number" value={weight} onChange={(e) => setWeight(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Passport Number</label>
              <Input value={passport} onChange={(e) => setPassport(e.target.value)} />
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
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Saving...' : 'Add Passenger'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
