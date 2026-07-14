import { useState, useEffect, type FormEvent } from 'react'
import { Wrench, Plus, AlertTriangle, Clock, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

interface MxTask {
  id: string
  aircraft_id: string
  title: string
  description: string | null
  task_type: string
  status: string
  reference: string | null
  interval_hours: number | null
  interval_days: number | null
  scheduled_date: string | null
  completed_date: string | null
  completed_hours: number | null
  approved_by: string | null
  notes: string | null
  created_at: string
}

interface Aircraft {
  id: string
  tail_number: string
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  in_progress: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  completed: 'bg-green-500/10 text-green-500 border-green-500/20',
  overdue: 'bg-red-500/10 text-red-500 border-red-500/20',
  deferred: 'bg-muted text-muted-foreground border-border',
}

const TYPE_LABELS: Record<string, string> = {
  inspection: 'Inspection',
  oil_change: 'Oil Change',
  ad: 'AD',
  sb: 'SB',
  overhaul: 'Overhaul',
  repair: 'Repair',
  annual: 'Annual',
  '100hr': '100-Hour',
  phase: 'Phase',
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'bg-muted text-muted-foreground'
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  )
}

export default function MaintenancePage() {
  const [tasks, setTasks] = useState<MxTask[]>([])
  const [total, setTotal] = useState(0)
  const [overdueCount, setOverdueCount] = useState(0)
  const [dueSoonCount, setDueSoonCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [showAddDialog, setShowAddDialog] = useState(false)

  // Add form
  const [selectedAircraft, setSelectedAircraft] = useState('')
  const [mxTitle, setMxTitle] = useState('')
  const [mxType, setMxType] = useState('inspection')
  const [mxIntervalHrs, setMxIntervalHrs] = useState('')
  const [mxScheduledDate, setMxScheduledDate] = useState('')
  const [mxReference, setMxReference] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchTasks = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeTab === 'overdue') params.set('overdue', 'true')
      else if (activeTab === 'completed') params.set('status', 'completed')
      const res = await api.get(`/api/v1/maintenance?${params}`)
      setTasks(res.data.data)
      setTotal(res.data.total)
      setOverdueCount(res.data.overdue_count)
      setDueSoonCount(res.data.due_soon_count)
    } catch { /* silent */ }
    setLoading(false)
  }

  useEffect(() => { fetchTasks() }, [activeTab])

  useEffect(() => {
    api.get('/api/v1/aircraft?per_page=100').then((r) => setAircraft(r.data.data))
  }, [])

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedAircraft) return
    setSubmitting(true)
    try {
      await api.post('/api/v1/maintenance', {
        aircraft_id: selectedAircraft,
        title: mxTitle,
        task_type: mxType,
        reference: mxReference || undefined,
        interval_hours: mxIntervalHrs ? parseFloat(mxIntervalHrs) : undefined,
        scheduled_date: mxScheduledDate || undefined,
      })
      setShowAddDialog(false)
      setMxTitle('')
      setMxReference('')
      setMxIntervalHrs('')
      setMxScheduledDate('')
      await fetchTasks()
    } catch { /* silent */ }
    setSubmitting(false)
  }

  const handleComplete = async (task: MxTask) => {
    try {
      await api.patch(`/api/v1/maintenance/${task.id}`, { status: 'completed' })
      await fetchTasks()
    } catch { /* silent */ }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Maintenance</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {total} tasks · {overdueCount > 0 && <span className="text-red-500">{overdueCount} overdue</span>}
            {overdueCount > 0 && dueSoonCount > 0 && <span> · </span>}
            {dueSoonCount > 0 && <span className="text-amber-500">{dueSoonCount} due soon</span>}
          </p>
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Task
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className={overdueCount > 0 ? 'border-red-500/30' : ''}>
          <CardContent className="flex items-center gap-3 p-4">
            <AlertTriangle className={`h-8 w-8 ${overdueCount > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
            <div>
              <p className="text-2xl font-bold">{overdueCount}</p>
              <p className="text-sm text-muted-foreground">Overdue</p>
            </div>
          </CardContent>
        </Card>
        <Card className={dueSoonCount > 0 ? 'border-amber-500/30' : ''}>
          <CardContent className="flex items-center gap-3 p-4">
            <Clock className={`h-8 w-8 ${dueSoonCount > 0 ? 'text-amber-500' : 'text-muted-foreground'}`} />
            <div>
              <p className="text-2xl font-bold">{dueSoonCount}</p>
              <p className="text-sm text-muted-foreground">Due in 30 days</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-2xl font-bold">{tasks.filter((t) => t.status === 'completed').length}</p>
              <p className="text-sm text-muted-foreground">Completed</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">All ({total})</TabsTrigger>
          <TabsTrigger value="overdue" className={overdueCount > 0 ? 'text-red-500' : ''}>
            Overdue ({overdueCount})
          </TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse"><CardContent className="p-6"><div className="h-12 rounded bg-muted" /></CardContent></Card>
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <Wrench className="h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">No maintenance tasks</p>
              <Button onClick={() => setShowAddDialog(true)}>
                <Plus className="mr-2 h-4 w-4" /> Add Task
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => {
                const tail = aircraft.find((a) => a.id === task.aircraft_id)?.tail_number || '—'
                const isOverdue = task.status === 'overdue' || (task.status === 'scheduled' && task.scheduled_date && new Date(task.scheduled_date) < new Date())
                return (
                  <Card key={task.id} className={`border-border/50 ${isOverdue ? 'border-l-red-500' : ''}`}>
                    <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium truncate">{task.title}</span>
                          <StatusBadge status={isOverdue ? 'overdue' : task.status} />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                          <span>{tail}</span>
                          <span className="capitalize">{TYPE_LABELS[task.task_type] || task.task_type}</span>
                          {task.reference && <span className="font-mono text-xs">{task.reference}</span>}
                          {task.scheduled_date && <span>Due: {task.scheduled_date}</span>}
                          {task.interval_hours && <span>Every {task.interval_hours} hrs</span>}
                        </div>
                      </div>
                      {task.status !== 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="shrink-0"
                          onClick={() => handleComplete(task)}
                        >
                          <CheckCircle className="mr-1.5 h-3.5 w-3.5" /> Complete
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Task Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Maintenance Task</DialogTitle>
            <DialogDescription>Schedule maintenance for an aircraft.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Aircraft</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={selectedAircraft}
                onChange={(e) => setSelectedAircraft(e.target.value)}
                required
              >
                <option value="">Select aircraft...</option>
                {aircraft.map((a) => (
                  <option key={a.id} value={a.id}>{a.tail_number}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input placeholder="100-Hour Inspection" value={mxTitle} onChange={(e) => setMxTitle(e.target.value)} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Type</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={mxType} onChange={(e) => setMxType(e.target.value)}>
                  {Object.entries(TYPE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Interval (hours)</label>
                <Input type="number" placeholder="100" value={mxIntervalHrs} onChange={(e) => setMxIntervalHrs(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Scheduled Date</label>
                <Input type="date" value={mxScheduledDate} onChange={(e) => setMxScheduledDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">AD/SB Reference</label>
                <Input placeholder="AD 2024-08-15" value={mxReference} onChange={(e) => setMxReference(e.target.value)} />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Adding...' : 'Add Task'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
