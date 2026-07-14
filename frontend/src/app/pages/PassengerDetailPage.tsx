import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'

export default function PassengerDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [p, setP] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/passengers/${id}`)
      .then((res) => setP(res.data))
      .catch(() => navigate('/passengers'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!p) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/passengers')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{p.full_name}</h1>
            {p.nationality && <Badge variant="outline">{p.nationality}</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{p.total_flights} flights · Profile</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Identity</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {p.date_of_birth && <p><span className="text-muted-foreground">DOB: </span>{p.date_of_birth}</p>}
            {p.gender && <p><span className="text-muted-foreground">Gender: </span>{p.gender}</p>}
            {p.nationality && <p><span className="text-muted-foreground">Nationality: </span>{p.nationality}</p>}
            {p.weight_kg && <p><span className="text-muted-foreground">Weight: </span>{p.weight_kg} kg</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Travel Documents</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {p.passport_number && (
              <p>
                <span className="text-muted-foreground">Passport: </span>
                <span className="font-mono">{p.passport_number}</span>
                {p.passport_expiry && <span className="ml-2 text-muted-foreground">(exp: {p.passport_expiry})</span>}
              </p>
            )}
            {p.id_number && <p><span className="text-muted-foreground">ID #: </span>{p.id_number}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Contact</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {p.email && <p><span className="text-muted-foreground">Email: </span>{p.email}</p>}
            {p.phone && <p><span className="text-muted-foreground">Phone: </span>{p.phone}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Flight History</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p><span className="text-muted-foreground">Total flights: </span>{p.total_flights}</p>
            {p.first_flight && <p><span className="text-muted-foreground">First flight: </span>{p.first_flight}</p>}
            {p.last_flight && <p><span className="text-muted-foreground">Last flight: </span>{p.last_flight}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
