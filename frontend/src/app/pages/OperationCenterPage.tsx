import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Gauge,
  Plane,
  Wrench,
  AlertTriangle,
  Weight,
  RefreshCw,
  ArrowUpRight,
  ChevronRight,
  CloudSun,
  FileWarning,
  AlertOctagon,
  MessageSquare,
  Send,
  ChevronDown,
  ChevronRight as ChevronRightIcon,
  Check,
  X,
  ShieldAlert,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import LiveTrackingMap from '@/features/tracking/LiveTrackingMap'
import api from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

interface SummaryCard {
  label: string
  value: number
  icon: React.ReactNode
  color: string
  link?: string
}

interface RecentMission {
  id: string
  title: string
  flight_number: string
  aircraft_tail: string
  departure: string
  arrival: string
  status: 'draft' | 'active' | 'completed' | 'cancelled'
  pic: string
  leg_count: number
}

interface ParsedMetar {
  wind: string
  visibility: string
  ceiling: string
  flightCategory: 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'N/A'
}

interface WeatherAirportRow {
  icao: string
  metar: string
  flightCategory: 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'N/A'
  wind: string
  visibility: string
  ceiling: string
  notam_count: number
}

type EmergencySeverity = 'low' | 'medium' | 'high' | 'critical'

interface EmergencyAlert {
  id: string
  title: string
  description: string
  severity: EmergencySeverity
  aircraft_id?: string | null
  flight_id?: string | null
  status: 'active' | 'acknowledged' | 'resolved'
  created_at: string
  created_by?: string
}

interface CrewMessage {
  id: string
  sender: string
  message: string
  timestamp: string
  read: boolean
}

// ── Mock data ───────────────────────────────────────────────────────────────

const MOCK_SUMMARY = {
  active_missions: 4,
  aircraft_in_maintenance: 2,
  upcoming_duty_violations: 1,
  open_weight_warnings: 3,
  weather_advisories: 2,
  active_notams: 5,
}

const MOCK_RECENT_MISSIONS: RecentMission[] = [
  { id: 'm1', title: 'Caribbean Loop Challenge', flight_number: 'PRC-101', aircraft_tail: 'N701PR', departure: 'MYNN', arrival: 'MYNN', status: 'active', pic: 'Capt. Jack D.', leg_count: 6 },
  { id: 'm2', title: 'Bahamas Medevac Run', flight_number: 'PRC-205', aircraft_tail: 'N702PR', departure: 'MYGF', arrival: 'KFLL', status: 'active', pic: 'Capt. Maria R.', leg_count: 1 },
  { id: 'm3', title: 'Turks & Caicos Supply', flight_number: 'PRC-108', aircraft_tail: 'N703PR', departure: 'MBPV', arrival: 'MDPC', status: 'draft', pic: 'FO Sarah K.', leg_count: 2 },
  { id: 'm4', title: 'Havana Diplomatic Run', flight_number: 'PRC-315', aircraft_tail: 'N701PR', departure: 'KMIA', arrival: 'MUHA', status: 'active', pic: 'Capt. Jack D.', leg_count: 1 },
  { id: 'm5', title: 'Fleet Positioning', flight_number: 'PRC-022', aircraft_tail: 'N704PR', departure: 'MYNN', arrival: 'TIST', status: 'completed', pic: 'FO Dave M.', leg_count: 3 },
  { id: 'm6', title: 'Aircraft Ferry KEF', flight_number: 'PRC-901', aircraft_tail: 'N705PR', departure: 'MYNN', arrival: 'BIKF', status: 'cancelled', pic: 'Capt. Jack D.', leg_count: 4 },
]

// Realistic METAR strings for Caribbean / Bahamas route airports
const MOCK_WEATHER_METARS: Record<string, string> = {
  MYNN: 'MYNN 161500Z 28012G18KT 10SM FEW025 SCT045 30/22 Q1015',
  KMIA: 'KMIA 161453Z 25010KT 10SM FEW030 SCT250 31/23 A3003',
  MMUN: 'MMUN 161500Z 14008KT 4SM -RA BKN012 BKN040 28/24 Q1013',
  MTPP: 'MTPP 161500Z 10006KT 2SM RA BKN008 OVC020 26/24 Q1012',
  MUHA: 'MUHA 161500Z 09010G20KT 2SM -TSRA BKN015 FEW023CB OVC040 27/23 Q1013',
  MDPC: 'MDPC 161500Z 07008KT 10SM FEW025 30/26 Q1014',
}

const MOCK_NOTAM_COUNTS: Record<string, number> = {
  MYNN: 1,
  KMIA: 1,
  MMUN: 1,
  MTPP: 1,
  MUHA: 1,
  MDPC: 0,
}

// Mock crew messages for ops comms
const MOCK_MESSAGES: CrewMessage[] = [
  { id: 'cm1', sender: 'N101PB', message: 'Departing MYNN, wheels up 14:32Z', timestamp: '2025-07-16T14:32:00Z', read: true },
  { id: 'cm2', sender: 'Ops', message: 'Copy, weather at MTPP is IFR, advise fuel stop at KMIA', timestamp: '2025-07-16T14:33:00Z', read: true },
  { id: 'cm3', sender: 'N102PR', message: 'Requesting latest NOTAMs for MDPC', timestamp: '2025-07-16T14:45:00Z', read: false },
  { id: 'cm4', sender: 'Ops', message: 'N102PR, MDPC RWY 10/29 closed for maintenance until 1800Z. Advise RWY 05/23', timestamp: '2025-07-16T14:46:00Z', read: false },
  { id: 'cm5', sender: 'N103PR', message: 'Enroute MYNN-KMIA, FL250, eta 15:10Z, 4 pax', timestamp: '2025-07-16T14:52:00Z', read: false },
  { id: 'cm6', sender: 'Ops', message: 'All crews: Tropical Storm Alberto forecast update at 18Z. Expect routing changes.', timestamp: '2025-07-16T15:00:00Z', read: false },
]

const FLEET_TAIL_NUMBERS = ['N701PR', 'N702PR', 'N703PR', 'N704PR', 'N705PR']

// ── Status helpers ─────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  active: { label: 'Active', color: 'bg-green-500/10 text-green-500 border-green-500/20' },
  draft: { label: 'Draft', color: 'bg-muted text-muted-foreground border-border/30' },
  completed: { label: 'Completed', color: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
  cancelled: { label: 'Cancelled', color: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
}

const SEVERITY_CONFIG: Record<EmergencySeverity, { label: string; color: string; icon: React.ReactNode }> = {
  low: { label: 'Low', color: 'bg-blue-500/10 text-blue-500 border-blue-500/20', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  medium: { label: 'Medium', color: 'bg-amber-500/10 text-amber-500 border-amber-500/20', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  high: { label: 'High', color: 'bg-orange-500/10 text-orange-500 border-orange-500/20', icon: <ShieldAlert className="h-3.5 w-3.5" /> },
  critical: { label: 'Critical', color: 'bg-red-500/10 text-red-500 border-red-500/20', icon: <AlertOctagon className="h-3.5 w-3.5" /> },
}

// ── METAR Parser ────────────────────────────────────────────────────────────

function parseMetar(metar: string): ParsedMetar {
  const empty: ParsedMetar = {
    wind: '—', visibility: '—', ceiling: '—', flightCategory: 'N/A',
  }
  if (!metar || metar.trim() === '') return empty

  // Wind: 3-digit direction + 2-digit speed, optional G gust, KT/MPS
  const windMatch = metar.match(/(\d{3})(\d{2})G?(\d{0,2})(?:KT|MPS)/)
  const wind = windMatch
    ? `${windMatch[1]}°/${windMatch[2]}${windMatch[3] ? `G${windMatch[3]}` : ''}kt`
    : '—'

  // Visibility
  let visibility = '—'
  let visSm = -1
  const visSmMatch = metar.match(/(\d+\s?\d?\/?\d*)SM/)
  const visMetricMatch = metar.match(/\s(\d{4})\s/)
  if (visSmMatch) {
    const raw = visSmMatch[1]
    if (raw.includes('/')) {
      const parts = raw.replace(/\s+/g, '').split('/')
      visSm = parseFloat(parts[0]) / parseFloat(parts[1])
    } else {
      visSm = parseFloat(raw)
    }
    visibility = raw.trim() + ' SM'
  } else if (visMetricMatch) {
    const v = parseInt(visMetricMatch[1])
    visibility = v >= 9999 ? '10+ km (CAVOK)' : `${v} m`
    visSm = v >= 9999 ? 10 : v / 1000
  }
  if (metar.includes('CAVOK')) {
    visibility = 'CAVOK'
    visSm = 10
  }

  // Clouds & ceiling
  let ceiling = '—'
  let ceiling_ft = 99999
  const cloudMatch = metar.match(/(BKN|OVC)(\d{3})/)
  if (cloudMatch) {
    ceiling_ft = parseInt(cloudMatch[2]) * 100
    ceiling = `${cloudMatch[1]} at ${ceiling_ft}ft`
  } else {
    const fewMatch = metar.match(/FEW(\d{3})/)
    if (fewMatch) ceiling = `FEW at ${parseInt(fewMatch[1]) * 100}ft`
    else {
      const sctMatch = metar.match(/SCT(\d{3})/)
      if (sctMatch) ceiling = `SCT at ${parseInt(sctMatch[1]) * 100}ft`
    }
  }

  // Flight category
  let flightCategory: 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'N/A' = 'N/A'
  if (ceiling_ft >= 3000 && visSm >= 5) flightCategory = 'VFR'
  else if (ceiling_ft >= 1000 && visSm >= 3) flightCategory = 'MVFR'
  else if (ceiling_ft >= 500 && visSm >= 1) flightCategory = 'IFR'
  else if (ceiling_ft < 99999) flightCategory = 'LIFR'

  return { wind, visibility, ceiling, flightCategory }
}

// ── Flight Category Badge colors ────────────────────────────────────────────

const FC_BADGE_CLASSES: Record<string, string> = {
  VFR: 'bg-green-500/10 text-green-500 border-green-500/20',
  MVFR: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  IFR: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  LIFR: 'bg-red-500/10 text-red-500 border-red-500/20',
  'N/A': 'bg-muted text-muted-foreground border-border/30',
}

const FC_ROW_CLASSES: Record<string, string> = {
  VFR: 'border-green-500/10',
  MVFR: 'border-blue-500/10',
  IFR: 'border-amber-500/20',
  LIFR: 'border-red-500/20',
  'N/A': 'border-transparent',
}

// ── Build weather airport rows from METARs ──────────────────────────────────

function buildWeatherRows(
  metars: Record<string, string>,
  notamCounts: Record<string, number>,
): WeatherAirportRow[] {
  return Object.entries(metars).map(([icao, metar]) => {
    const parsed = parseMetar(metar)
    return {
      icao,
      metar,
      flightCategory: parsed.flightCategory,
      wind: parsed.wind,
      visibility: parsed.visibility,
      ceiling: parsed.ceiling,
      notam_count: notamCounts[icao] ?? 0,
    }
  })
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ${mins % 60}m ago`
}

// ── Summary Card Grid (2×3) — compact ─────────────────────────────────────

function SummaryCardGrid({ cards }: { cards: SummaryCard[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.label} className="border-border/50 transition-colors hover:border-border/80">
          <CardContent className="flex items-center justify-between p-3">
            <div className="flex flex-col">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                {card.label}
              </span>
              <span className="mt-0.5 text-xl font-bold leading-none">{card.value}</span>
              {card.link && (
                <a
                  href={card.link}
                  className="mt-1 inline-flex items-center gap-0.5 text-[10px] text-brand-400 hover:text-brand-300"
                >
                  View <ArrowUpRight className="h-2.5 w-2.5" />
                </a>
              )}
            </div>
            <div className={`rounded-full p-1.5 ${card.color}`}>
              {card.icon}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Active Alerts Banner ────────────────────────────────────────────────────

function ActiveAlertsBanner({
  alerts,
  onAcknowledge,
  onResolve,
}: {
  alerts: EmergencyAlert[]
  onAcknowledge: (id: string) => void
  onResolve: (id: string) => void
}) {
  const activeAlerts = alerts.filter((a) => a.status === 'active')
  if (activeAlerts.length === 0) return null

  const criticalCount = activeAlerts.filter((a) => a.severity === 'critical').length
  const highCount = activeAlerts.filter((a) => a.severity === 'high').length

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <AlertOctagon className="h-5 w-5 animate-pulse text-red-500" />
          <div>
            <span className="text-sm font-semibold text-red-500">
              {activeAlerts.length} ACTIVE EMERGENCY ALERT{activeAlerts.length > 1 ? 'S' : ''}
            </span>
            <span className="ml-2 text-xs text-red-400">
              {criticalCount > 0 && `${criticalCount} critical`}
              {criticalCount > 0 && highCount > 0 && ' · '}
              {highCount > 0 && `${highCount} high`}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {activeAlerts.map((alert) => {
            const sev = SEVERITY_CONFIG[alert.severity]
            return (
              <div key={alert.id} className="flex items-center gap-2 rounded-md bg-background/40 px-3 py-1.5 text-xs">
                <span className={`${sev.color.split(' ')[0]} rounded px-1 py-0.5 font-medium`}>
                  {sev.label}
                </span>
                <span className="max-w-[160px] truncate text-red-200">{alert.title}</span>
                <button
                  onClick={() => onAcknowledge(alert.id)}
                  className="text-red-400 hover:text-red-300"
                  title="Acknowledge"
                >
                  <Check className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onResolve(alert.id)}
                  className="text-red-400 hover:text-green-400"
                  title="Resolve"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Emergency Alert Dialog ──────────────────────────────────────────────────

function EmergencyAlertDialog({
  open,
  onOpenChange,
  onCreateAlert,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onCreateAlert: (data: { title: string; description: string; severity: EmergencySeverity; aircraft_id?: string }) => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState<EmergencySeverity>('high')
  const [aircraftId, setAircraftId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required'); return }
    setSubmitting(true)
    setError('')
    try {
      await onCreateAlert({
        title: title.trim(),
        description: description.trim(),
        severity,
        aircraft_id: aircraftId || undefined,
      })
      // Reset form
      setTitle('')
      setDescription('')
      setSeverity('high')
      setAircraftId('')
      onOpenChange(false)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create alert')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-500">
            <AlertOctagon className="h-5 w-5" />
            Create Emergency Alert
          </DialogTitle>
          <DialogDescription>
            Broadcast an urgent alert to all connected crew members.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              value={title}
              onChange={(e) => { setTitle(e.target.value); setError('') }}
              placeholder="e.g., Engine fire on N701PR"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              required
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed information about the emergency..."
              rows={3}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as EmergencySeverity)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Aircraft (optional)</label>
            <select
              value={aircraftId}
              onChange={(e) => setAircraftId(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">All aircraft / Not specified</option>
              {FLEET_TAIL_NUMBERS.map((tail) => (
                <option key={tail} value={tail}>{tail}</option>
              ))}
            </select>
          </div>

          {error && (
            <div className="rounded-md border border-red-500/20 bg-red-500/5 p-2 text-xs text-red-500">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="bg-red-600 hover:bg-red-700 text-white">
              {submitting ? 'Sending...' : 'Send Emergency Alert'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Crew Communications Panel ───────────────────────────────────────────────

function CrewCommsPanel({ messages, onSendMessage }: {
  messages: CrewMessage[]
  onSendMessage: (text: string) => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [inputValue, setInputValue] = useState('')

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text) return
    onSendMessage(text)
    setInputValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Card className="border-border/50">
      <CardHeader
        className="flex cursor-pointer flex-row items-center justify-between pb-3"
        onClick={() => setCollapsed(!collapsed)}
      >
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquare className="h-4 w-4 text-brand-400" />
          Crew Comms
          <Badge variant="outline" className="bg-brand-500/10 text-brand-500 border-brand-500/20 text-xs">
            {messages.filter((m) => !m.read).length} unread
          </Badge>
        </CardTitle>
        <div className="text-muted-foreground">
          {collapsed ? <ChevronRightIcon className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </CardHeader>
      {!collapsed && (
        <CardContent className="space-y-3 pt-0">
          {/* Messages list */}
          <div className="max-h-[240px] space-y-2 overflow-y-auto rounded-md border border-border/30 bg-muted/10 p-3">
            {messages.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">No messages yet.</p>
            ) : (
              [...messages].reverse().map((msg) => {
                const isOps = msg.sender === 'Ops'
                return (
                  <div
                    key={msg.id}
                    className={`rounded-md px-3 py-2 text-xs ${
                      !msg.read ? 'border-l-2 border-brand-400 bg-brand-500/5' : 'bg-background/40'
                    } ${isOps ? 'ml-4' : ''}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-semibold ${isOps ? 'text-brand-400' : 'text-foreground'}`}>
                        {msg.sender}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground" title={new Date(msg.timestamp).toLocaleString()}>
                          {fmtRelative(msg.timestamp)}
                        </span>
                        {!msg.read && (
                          <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
                        )}
                      </div>
                    </div>
                    <p className="mt-0.5 text-muted-foreground">{msg.message}</p>
                  </div>
                )
              })
            )}
          </div>

          {/* Input area */}
          <div className="flex items-end gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message to crew..."
              rows={2}
              className="min-h-[40px] flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            <Button
              type="button"
              size="icon"
              onClick={handleSend}
              disabled={!inputValue.trim()}
              className="h-10 w-10 shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

// ── Weather & Airspace Briefing Table ───────────────────────────────────────

function WeatherBriefingTable({
  rows,
  refreshing,
  onRefresh,
}: {
  rows: WeatherAirportRow[]
  refreshing: boolean
  onRefresh: () => void
}) {
  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <CloudSun className="h-4 w-4 text-brand-400" />
          Weather & Airspace Briefing
        </CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh Weather'}
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border/50 text-muted-foreground">
                <th className="py-3 pl-4 pr-3 font-medium">Airport</th>
                <th className="py-3 pr-3 font-medium">Flight Category</th>
                <th className="py-3 pr-3 font-medium">Wind</th>
                <th className="py-3 pr-3 font-medium">Visibility</th>
                <th className="py-3 pr-3 font-medium">Ceiling</th>
                <th className="py-3 pr-3 font-medium">NOTAMs</th>
                <th className="py-3 pr-4 font-medium">METAR (Raw)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const rowBorder = FC_ROW_CLASSES[row.flightCategory] || 'border-transparent'
                return (
                  <tr
                    key={row.icao}
                    className={`border-b ${rowBorder} transition-colors hover:bg-muted/20`}
                  >
                    <td className="py-3 pl-4 pr-3 font-medium">{row.icao}</td>
                    <td className="py-3 pr-3">
                      <Badge
                        variant="outline"
                        className={`font-mono text-xs ${FC_BADGE_CLASSES[row.flightCategory] || ''}`}
                      >
                        {row.flightCategory}
                      </Badge>
                    </td>
                    <td className="py-3 pr-3 font-mono text-xs">{row.wind}</td>
                    <td className="py-3 pr-3 text-xs">{row.visibility}</td>
                    <td className="py-3 pr-3 text-xs">{row.ceiling}</td>
                    <td className="py-3 pr-3">
                      {row.notam_count > 0 ? (
                        <span className="font-medium text-amber-500">{row.notam_count}</span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="max-w-[240px] py-3 pr-4">
                      <span className="block truncate font-mono text-xs text-muted-foreground" title={row.metar}>
                        {row.metar}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Recent Missions Table ──────────────────────────────────────────────────

function MissionsTable({ missions }: { missions: RecentMission[] }) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border/50 text-muted-foreground">
            <th className="py-3 pr-4 font-medium">Title</th>
            <th className="py-3 pr-4 font-medium">Flight</th>
            <th className="py-3 pr-4 font-medium">Aircraft</th>
            <th className="py-3 pr-4 font-medium">Route</th>
            <th className="py-3 pr-4 font-medium">PIC</th>
            <th className="py-3 pr-4 font-medium">Legs</th>
            <th className="py-3 pr-4 font-medium">Status</th>
            <th className="py-3 font-medium" />
          </tr>
        </thead>
        <tbody>
          {missions.map((m) => {
            const s = STATUS_STYLES[m.status] || { label: m.status, color: '' }
            return (
              <tr
                key={m.id}
                className="cursor-pointer border-b border-border/20 transition-colors hover:bg-muted/30"
                onClick={() => navigate(`/missions/${m.id}`)}
              >
                <td className="py-3 pr-4 font-medium">{m.title}</td>
                <td className="py-3 pr-4 font-mono text-xs">{m.flight_number}</td>
                <td className="py-3 pr-4">{m.aircraft_tail}</td>
                <td className="py-3 pr-4">
                  <span className="font-medium">{m.departure}</span>
                  <ChevronRight className="mx-1 inline h-3 w-3 text-muted-foreground" />
                  <span className="font-medium">{m.arrival}</span>
                </td>
                <td className="py-3 pr-4 text-muted-foreground">{m.pic}</td>
                <td className="py-3 pr-4">{m.leg_count}</td>
                <td className="py-3 pr-4">
                  <Badge variant="outline" className={s.color}>
                    {s.label}
                  </Badge>
                </td>
                <td className="py-3">
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function OperationCenterPage() {
  const [summary, setSummary] = useState(MOCK_SUMMARY)
  const [missions, setMissions] = useState<RecentMission[]>(MOCK_RECENT_MISSIONS)
  const [refreshing, setRefreshing] = useState(false)
  const [weatherRows, setWeatherRows] = useState<WeatherAirportRow[]>(() =>
    buildWeatherRows(MOCK_WEATHER_METARS, MOCK_NOTAM_COUNTS),
  )
  const [weatherRefreshing, setWeatherRefreshing] = useState(false)

  // Emergency alert state
  const [emergencyAlerts, setEmergencyAlerts] = useState<EmergencyAlert[]>(() => {
    // Load from localStorage if available (survives page refresh during session)
    const stored = localStorage.getItem('pararig_emergency_alerts')
    if (stored) {
      try { return JSON.parse(stored) } catch {}
    }
    return []
  })
  const [showEmergencyDialog, setShowEmergencyDialog] = useState(false)

  // Crew comms state
  const [crewMessages, setCrewMessages] = useState<CrewMessage[]>(MOCK_MESSAGES)

  // Persist alerts
  const persistAlerts = (alerts: EmergencyAlert[]) => {
    setEmergencyAlerts(alerts)
    localStorage.setItem('pararig_emergency_alerts', JSON.stringify(alerts))
  }

  // ── Emergency alert handlers ──────────────────────────────────────────────

  const handleCreateEmergency = async (data: {
    title: string
    description: string
    severity: EmergencySeverity
    aircraft_id?: string
  }) => {
    // Try real API first
    try {
      const res = await api.post('/api/v1/comms/emergency', data)
      const newAlert: EmergencyAlert = res.data
      persistAlerts([newAlert, ...emergencyAlerts])
      return
    } catch {
      // Fallback: create locally
    }

    const newAlert: EmergencyAlert = {
      id: `emerg-${Date.now()}`,
      title: data.title,
      description: data.description,
      severity: data.severity,
      aircraft_id: data.aircraft_id || null,
      flight_id: null,
      status: 'active',
      created_at: new Date().toISOString(),
      created_by: 'Ops Center',
    }
    persistAlerts([newAlert, ...emergencyAlerts])
  }

  const handleAcknowledgeAlert = async (id: string) => {
    try {
      await api.post(`/api/v1/comms/emergency/${id}/acknowledge`)
    } catch {
      // local fallback
    }
    persistAlerts(
      emergencyAlerts.map((a) => (a.id === id ? { ...a, status: 'acknowledged' as const } : a)),
    )
  }

  const handleResolveAlert = async (id: string) => {
    try {
      await api.post(`/api/v1/comms/emergency/${id}/resolve`)
    } catch {
      // local fallback
    }
    persistAlerts(
      emergencyAlerts.map((a) => (a.id === id ? { ...a, status: 'resolved' as const } : a)),
    )
  }

  // ── Crew comms handlers ───────────────────────────────────────────────────

  const handleSendMessage = (text: string) => {
    const newMsg: CrewMessage = {
      id: `cm-${Date.now()}`,
      sender: 'Ops',
      message: text,
      timestamp: new Date().toISOString(),
      read: true,
    }
    setCrewMessages((prev) => [...prev, newMsg])
  }

  // ── Data fetching ─────────────────────────────────────────────────────────

  const fetchData = async () => {
    setRefreshing(true)
    try {
      const [summaryRes, missionsRes] = await Promise.all([
        api.get('/api/v1/operations/summary').catch(() => null),
        api.get('/api/v1/operations/recent-missions').catch(() => null),
      ])
      if (summaryRes?.data) setSummary(summaryRes.data)
      if (missionsRes?.data) setMissions(missionsRes.data)
    } catch {
      // keep mock data
    }
    // Also try fetching active emergencies from API
    try {
      const emRes = await api.get('/api/v1/comms/emergency')
      if (emRes.data && Array.isArray(emRes.data)) {
        setEmergencyAlerts(emRes.data)
      }
    } catch {
      // keep local state
    }
    setRefreshing(false)
  }

  const refreshWeather = async () => {
    setWeatherRefreshing(true)
    try {
      // Try ops-checks/weather endpoint first
      const weatherRes = await api.get('/api/v1/ops-checks/weather').catch(() => null)
      if (weatherRes?.data) {
        // If we get live data with metars, use it
        const liveMetars = weatherRes.data.metars as Record<string, string> | undefined
        const liveNotams = weatherRes.data.notam_counts as Record<string, number> | undefined
        if (liveMetars) {
          setWeatherRows(buildWeatherRows(liveMetars, liveNotams ?? MOCK_NOTAM_COUNTS))
          setWeatherRefreshing(false)
          return
        }
      }
      setWeatherRows(buildWeatherRows(MOCK_WEATHER_METARS, MOCK_NOTAM_COUNTS))
    } catch {
      setWeatherRows(buildWeatherRows(MOCK_WEATHER_METARS, MOCK_NOTAM_COUNTS))
    }
    setWeatherRefreshing(false)
  }

  // Count advisories: airports with IFR/LIFR conditions
  const weatherAdvisoryCount = weatherRows.filter(
    (r) => r.flightCategory === 'IFR' || r.flightCategory === 'LIFR',
  ).length

  // Count total active NOTAMs
  const totalNotams = weatherRows.reduce((sum, r) => sum + r.notam_count, 0)

  const summaryCards: SummaryCard[] = [
    {
      label: 'Active Missions',
      value: summary.active_missions,
      icon: <Plane className="h-4 w-4 text-green-500" />,
      color: 'bg-green-500/10',
      link: '/missions',
    },
    {
      label: 'Aircraft In Maintenance',
      value: summary.aircraft_in_maintenance,
      icon: <Wrench className="h-4 w-4 text-amber-500" />,
      color: 'bg-amber-500/10',
      link: '/maintenance',
    },
    {
      label: 'Upcoming Duty Violations',
      value: summary.upcoming_duty_violations,
      icon: <AlertTriangle className="h-4 w-4 text-red-500" />,
      color: 'bg-red-500/10',
      link: '/crew',
    },
    {
      label: 'Open Weight Warnings',
      value: summary.open_weight_warnings,
      icon: <Weight className="h-4 w-4 text-amber-500" />,
      color: 'bg-amber-500/10',
      link: '/dispatch',
    },
    {
      label: 'Weather Advisories',
      value: weatherAdvisoryCount,
      icon: <CloudSun className="h-4 w-4 text-blue-500" />,
      color: weatherAdvisoryCount > 0 ? 'bg-amber-500/10' : 'bg-blue-500/10',
      link: undefined,
    },
    {
      label: 'Active NOTAMs / TFRs',
      value: totalNotams,
      icon: <FileWarning className="h-4 w-4 text-amber-500" />,
      color: totalNotams > 0 ? 'bg-amber-500/10' : 'bg-green-500/10',
      link: undefined,
    },
  ]

  return (
    <div className="space-y-4">
      {/* Active Alerts Banner */}
      <ActiveAlertsBanner
        alerts={emergencyAlerts}
        onAcknowledge={handleAcknowledgeAlert}
        onResolve={handleResolveAlert}
      />

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-brand-500/10 p-2">
            <Gauge className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Operation Center</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Real-time operational overview · Part 135 Ops
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="destructive"
            className="animate-pulse bg-red-600 hover:bg-red-700"
            onClick={() => setShowEmergencyDialog(true)}
          >
            <AlertOctagon className="mr-2 h-4 w-4" />
            EMERGENCY
          </Button>
          <Button variant="outline" onClick={fetchData} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh All'}
          </Button>
        </div>
      </div>

      {/* Live Flight Following Map */}
      <LiveTrackingMap />

      {/* Summary Card Grid (2×3) */}
      <SummaryCardGrid cards={summaryCards} />

      {/* Crew Comms Panel */}
      <CrewCommsPanel messages={crewMessages} onSendMessage={handleSendMessage} />

      {/* Weather & Airspace Briefing */}
      <WeatherBriefingTable
        rows={weatherRows}
        refreshing={weatherRefreshing}
        onRefresh={refreshWeather}
      />

      {/* Recent Missions */}
      <Card className="border-border/50">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Plane className="h-4 w-4 text-brand-400" />
            Recent Missions
          </CardTitle>
          <Badge variant="outline" className="bg-brand-500/10 text-brand-500 border-brand-500/20">
            {missions.length} total
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {missions.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <Plane className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No missions found.</p>
            </div>
          ) : (
            <MissionsTable missions={missions} />
          )}
        </CardContent>
      </Card>

      {/* Emergency Alert Dialog */}
      <EmergencyAlertDialog
        open={showEmergencyDialog}
        onOpenChange={setShowEmergencyDialog}
        onCreateAlert={handleCreateEmergency}
      />

      {/* Footer info */}
      <p className="text-center text-xs text-muted-foreground">
        Data refreshes automatically. Use the Refresh button to pull latest from operations API.
      </p>
    </div>
  )
}
