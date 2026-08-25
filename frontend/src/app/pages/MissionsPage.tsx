import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MapPin, Plane } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface Mission {
  id: string
  status: string
  aircraft_id: string | null
  home_base: string
  mission_date: string | null
  mission_number: string | null
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
            <div className="space-y-2">{[1,2,3].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
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
            <div className="overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-3 pl-4 pr-3 font-medium">Mission</th>
                    <th className="py-3 pr-3 font-medium">Route</th>
                    <th className="py-3 pr-3 font-medium text-right">Legs</th>
                    <th className="py-3 pr-3 font-medium">Base</th>
                    <th className="py-3 pr-3 font-medium">Date</th>
                    <th className="py-3 pr-4 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {missions.map((m) => {
                    const route = m.legs?.length > 0
                      ? `${m.legs.map((l: any) => l.departure_airport).join(' → ')} → ${m.legs[m.legs.length - 1].arrival_airport}`
                      : 'No legs'
                    const legCount = m.legs?.length || 0
                    return (
                      <tr
                        key={m.id}
                        className="cursor-pointer border-b border-border/10 transition-colors hover:bg-muted/30"
                        onClick={() => navigate(`/missions/${m.id}`)}
                      >
                        <td className="py-3 pl-4 pr-3">
                          <div className="flex items-center gap-2">
                            <Plane className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="font-medium">{m.mission_number || m.id.slice(0, 8)}</span>
                          </div>
                        </td>
                        <td className="py-3 pr-3 text-muted-foreground max-w-[300px] truncate" title={route}>
                          {route}
                        </td>
                        <td className="py-3 pr-3 text-right">{legCount}</td>
                        <td className="py-3 pr-3">{m.home_base}</td>
                        <td className="py-3 pr-3">{m.mission_date || '—'}</td>
                        <td className="py-3 pr-4">
                          <Badge variant="outline" className={STATUS_COLORS[m.status] || ''}>
                            {m.status}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
