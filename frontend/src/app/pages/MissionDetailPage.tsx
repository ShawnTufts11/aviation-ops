import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plane, MapPin, Users, Fuel, FileWarning, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'

export default function MissionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get(`/api/v1/missions/${id}`)
      .then((res) => setData(res.data))
      .catch(() => navigate('/missions'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>
  if (!data) return null

  const { mission, warnings } = data
  const legs = mission.legs || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/missions')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Mission</h1>
            <Badge className={
              mission.status === 'active' ? 'bg-green-500' :
              mission.status === 'completed' ? 'bg-blue-500' : ''
            }>{mission.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {legs.length > 0 && `${legs[0].departure_airport} → ${legs[legs.length-1].arrival_airport} · `}
            {mission.home_base} base
          </p>
        </div>
      </div>

      {/* Warnings */}
      {warnings?.length > 0 && (
        <div className="space-y-2">
          {warnings.map((w: string, i: number) => (
            <div key={i} className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-500">
              <FileWarning className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Leg Timeline */}
      <Card>
        <CardHeader><CardTitle className="text-base flex items-center gap-2"><MapPin className="h-4 w-4" /> Route</CardTitle></CardHeader>
        <CardContent>
          <div className="relative space-y-0">
            {legs.map((leg: any, i: number) => (
              <div key={leg.id} className="flex gap-4 pb-6 last:pb-0">
                {/* Timeline line */}
                <div className="flex flex-col items-center">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                    leg.status === 'completed' ? 'bg-green-500 text-white' :
                    leg.status === 'active' ? 'bg-amber-500 text-white' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {leg.leg_number}
                  </div>
                  {i < legs.length - 1 && <div className="mt-1 h-full w-0.5 bg-border" />}
                </div>
                {/* Leg content */}
                <div className="flex-1 rounded-lg border border-border/50 p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{leg.departure_airport} → {leg.arrival_airport}</p>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                        {leg.distance_nm && <span>{leg.distance_nm} nm</span>}
                        {leg.fuel_required_l && <span className="flex items-center gap-1"><Fuel className="h-3 w-3" />{leg.fuel_required_l}L req</span>}
                        {leg.fuel_on_board_l && <span>{leg.fuel_on_board_l}L onboard</span>}
                      </div>
                    </div>
                    <Badge variant="outline" className={
                      leg.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                      leg.status === 'active' ? 'bg-amber-500/10 text-amber-500' : ''
                    }>{leg.status}</Badge>
                  </div>
                  {leg.notams && (
                    <div className="mt-2 rounded bg-amber-500/5 px-2 py-1 text-xs text-amber-500">
                      NOTAM: {leg.notams}
                    </div>
                  )}
                  {/* Manifest summary */}
                  {leg.manifest_entries?.length > 0 && (
                    <div className="mt-2 border-t border-border/50 pt-2">
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Users className="h-3 w-3" />
                        {leg.manifest_entries.filter((e: any) => e.entry_type === 'passenger').length} passengers
                        {leg.manifest_entries.filter((e: any) => e.entry_type === 'cargo').length > 0 &&
                          ` · ${leg.manifest_entries.filter((e: any) => e.entry_type === 'cargo').length} cargo`
                        }
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        {mission.status === 'draft' && (
          <Button onClick={async () => {
            await api.patch(`/api/v1/missions/${mission.id}`, { status: 'active' })
            window.location.reload()
          }}>
            <Plane className="mr-2 h-4 w-4" /> Activate Mission
          </Button>
        )}
        {mission.status === 'active' && (
          <Button onClick={async () => {
            await api.patch(`/api/v1/missions/${mission.id}`, { status: 'completed' })
            window.location.reload()
          }}>
            <CheckCircle className="mr-2 h-4 w-4" /> Complete Mission
          </Button>
        )}
      </div>
    </div>
  )
}
