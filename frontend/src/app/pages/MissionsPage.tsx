import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MapPin, Plane } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface Mission {
  id: string
  status: string
  aircraft_id: string | null
  home_base: string
  mission_date: string | null
  legs: any[]
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  active: 'bg-green-500/10 text-green-500',
  completed: 'bg-blue-500/10 text-blue-500',
  cancelled: 'bg-red-500/10 text-red-500',
}

export default function MissionsPage() {
  const [missions, setMissions] = useState<Mission[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('all')
  const navigate = useNavigate()

  useEffect(() => {
    const params = tab !== 'all' ? `?status=${tab}` : ''
    api.get(`/api/v1/missions${params}`)
      .then((res) => setMissions(res.data.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [tab])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Missions</h1>
          <p className="mt-1 text-sm text-muted-foreground">{missions.length} missions</p>
        </div>
        <Button onClick={() => navigate('/missions/new')}>
          <Plus className="mr-2 h-4 w-4" /> New Mission
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="draft">Drafts</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>

        <TabsContent value={tab} className="mt-4">
          {loading ? (
            <div className="space-y-3">{[1,2,3].map((i) => (
              <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-12 rounded bg-muted" /></CardContent></Card>
            ))}</div>
          ) : missions.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <MapPin className="h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">No missions yet</p>
              <Button onClick={() => navigate('/missions/new')}>
                <Plus className="mr-2 h-4 w-4" /> Create Mission
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {missions.map((m) => {
                const route = m.legs?.length > 0
                  ? `${m.legs[0].departure_airport} → ${m.legs[m.legs.length - 1].arrival_airport}`
                  : 'No legs'
                const legCount = m.legs?.length || 0
                return (
                  <Card
                    key={m.id}
                    className="cursor-pointer border-border/50 transition-colors hover:border-brand-500/50"
                    onClick={() => navigate(`/missions/${m.id}`)}
                  >
                    <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Plane className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{route}</span>
                          <Badge variant="outline" className={STATUS_COLORS[m.status] || ''}>
                            {m.status}
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {legCount} leg{legCount !== 1 ? 's' : ''} · {m.home_base}
                          {m.mission_date && ` · ${m.mission_date}`}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
