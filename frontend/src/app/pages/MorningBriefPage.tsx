import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Gauge,
  Plane,
  Wrench,
  MapPin,
  Wallet,
  ShieldCheck,
  CloudSun,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  AlertTriangle,
  AlertOctagon,
  Users,
  Calendar,
  Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthContext } from '@/features/auth/AuthContext'
import type { User } from '@/types'

// ── Types ──────────────────────────────────────────────────────────────────

interface Visibility {
  system_stats: boolean
  fleet_health: boolean
  parts_maintenance: boolean
  missions: boolean
  financials: boolean
  compliance: boolean
  weather: boolean
}

interface SystemStatsData {
  active_missions: number
  aircraft_airworthy: number
  aircraft_in_maintenance: number
  aircraft_grounded: number
  crew_on_duty: number
  flights_today: number
}

interface FleetAircraft {
  tail: string
  type: string
  status: string
  mission_capability: 'full' | 'partial' | 'not'
  safe_for_flight: boolean
}

interface MaintenanceItem {
  tail: string
  type: string
  items: {
    description: string
    due_date: string
    severity: 'overdue' | 'due_soon' | 'pending'
  }[]
  parts_needed: string[]
}

interface MissionItem {
  id: string
  name: string
  route: string
  aircraft: string
  pic: string
  status: string
  departure_time: string
}

interface FinancialData {
  mtd_revenue: number
  mtd_costs: number
  mtd_variance: number
  variance_pct: number
  per_aircraft: { tail: string; revenue: number; costs: number; margin: number }[]
}

interface ComplianceData {
  expiring_documents: number
  crew_currency_issues: number
  open_gripes: number
}

interface WeatherData {
  ifr_airports: string[]
  active_notams: number
  sigmets: number
}

// ── Mock Data ──────────────────────────────────────────────────────────────

const MOCK_SYSTEM_STATS: SystemStatsData = {
  active_missions: 0,
  aircraft_airworthy: 3,
  aircraft_in_maintenance: 1,
  aircraft_grounded: 0,
  crew_on_duty: 6,
  flights_today: 0,
}

const MOCK_FLEET: FleetAircraft[] = [
  { tail: 'N101PB', type: 'King Air 350', status: 'active', mission_capability: 'full', safe_for_flight: true },
  { tail: 'N202PB', type: '208 Caravan', status: 'active', mission_capability: 'full', safe_for_flight: true },
  { tail: 'N303PB', type: 'King Air 200', status: 'active', mission_capability: 'full', safe_for_flight: true },
  { tail: 'N404PB', type: 'BT-67', status: 'in_maintenance', mission_capability: 'not', safe_for_flight: false },
]

const MOCK_MAINTENANCE: MaintenanceItem[] = [
  {
    tail: 'N701PR', type: 'PC-12 NG',
    items: [
      { description: '100-hr inspection', due_date: '2025-08-10', severity: 'pending' },
      { description: 'ELT battery replacement', due_date: '2025-07-01', severity: 'overdue' },
    ],
    parts_needed: ['ELT battery kit (p/n 452-0032)'],
  },
  {
    tail: 'N703PR', type: 'C208B',
    items: [
      { description: 'Oil change', due_date: '2025-07-20', severity: 'due_soon' },
      { description: 'Landing gear inspection', due_date: '2025-08-01', severity: 'pending' },
    ],
    parts_needed: ['Oil filter (p/n 101-234)', 'Landing gear seal kit'],
  },
  {
    tail: 'N705PR', type: 'C208B',
    items: [
      { description: '50-hr inspection', due_date: '2025-06-15', severity: 'overdue' },
    ],
    parts_needed: ['Inspection panel gasket'],
  },
]

const MOCK_MISSIONS: MissionItem[] = [
  { id: 'm1', name: 'Caribbean Loop Challenge', route: 'MYNN→MYNN', aircraft: 'N701PR', pic: 'Capt. Jack D.', status: 'active', departure_time: '2025-07-16T14:00:00Z' },
  { id: 'm2', name: 'Bahamas Medevac Run', route: 'MYGF→KFLL', aircraft: 'N702PR', pic: 'Capt. Maria R.', status: 'active', departure_time: '2025-07-16T15:30:00Z' },
  { id: 'm3', name: 'Turks & Caicos Supply', route: 'MBPV→MDPC', aircraft: 'N704PR', pic: 'FO Sarah K.', status: 'draft', departure_time: '2025-07-17T10:00:00Z' },
  { id: 'm4', name: 'Havana Diplomatic Run', route: 'KMIA→MUHA', aircraft: 'N701PR', pic: 'Capt. Jack D.', status: 'active', departure_time: '2025-07-16T16:00:00Z' },
]

const MOCK_FINANCIALS: FinancialData = {
  mtd_revenue: 487_500,
  mtd_costs: 312_000,
  mtd_variance: 175_500,
  variance_pct: 36.0,
  per_aircraft: [
    { tail: 'N701PR', revenue: 185_000, costs: 98_000, margin: 87_000 },
    { tail: 'N702PR', revenue: 142_000, costs: 76_000, margin: 66_000 },
    { tail: 'N703PR', revenue: 0, costs: 45_000, margin: -45_000 },
    { tail: 'N704PR', revenue: 98_500, costs: 52_000, margin: 46_500 },
    { tail: 'N705PR', revenue: 62_000, costs: 41_000, margin: 21_000 },
  ],
}

const MOCK_COMPLIANCE: ComplianceData = {
  expiring_documents: 3,
  crew_currency_issues: 2,
  open_gripes: 5,
}

const MOCK_WEATHER: WeatherData = {
  ifr_airports: ['MTPP', 'MUHA', 'MMUN'],
  active_notams: 5,
  sigmets: 1,
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n)
}

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const STATUS_BADGE: Record<string, 'default' | 'secondary' | 'outline' | 'destructive' | 'success' | 'warning' | 'info'> = {
  active: 'success',
  draft: 'secondary',
  completed: 'info',
  cancelled: 'warning',
}

const SEVERITY_BADGE: Record<string, 'destructive' | 'warning' | 'secondary'> = {
  overdue: 'destructive',
  due_soon: 'warning',
  pending: 'secondary',
}

const CAPABILITY_BADGE: Record<string, 'success' | 'warning' | 'destructive'> = {
  full: 'success',
  partial: 'warning',
  not: 'destructive',
}

// ── Role gating ────────────────────────────────────────────────────────────

const FINANCE_ROLES = new Set(['super_admin', 'admin'])
const COMPLIANCE_ROLES = new Set(['super_admin', 'ops_manager', 'admin'])

function canViewFinance(role: User['role'] | null): boolean {
  return role ? FINANCE_ROLES.has(role) : false
}

function canViewCompliance(role: User['role'] | null): boolean {
  return role ? COMPLIANCE_ROLES.has(role) : false
}

function getRoleBadgeVariant(role: User['role'] | string | null): 'default' | 'secondary' | 'outline' | 'destructive' | 'success' | 'warning' | 'info' {
  if (!role) return 'secondary'
  if (role === 'super_admin') return 'destructive'
  if (role === 'admin' || role === 'ops_manager') return 'default'
  if (role === 'pilot') return 'info'
  return 'secondary'
}

// ── Collapsible Card Wrapper ───────────────────────────────────────────────

function CollapsibleCard({
  title,
  icon,
  defaultOpen = true,
  children,
}: {
  title: string
  icon: React.ReactNode
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Card className="border-border/50">
      <CardHeader
        className="flex cursor-pointer flex-row items-center justify-between pb-3"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <div className="rounded-md bg-primary/10 p-1.5 text-primary">
            {icon}
          </div>
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </CardHeader>
      {open && (
        <>
          <Separator className="mb-0" />
          <CardContent className="pt-4">{children}</CardContent>
        </>
      )}
    </Card>
  )
}

// ── Card 1: System Operating Stats ────────────────────────────────────────

function SystemStatsCard({ data }: { data: SystemStatsData }) {
  const totalAircraft = data.aircraft_airworthy + data.aircraft_in_maintenance + data.aircraft_grounded
  const statBoxes = [
    {
      label: 'Active Missions',
      value: data.active_missions,
      color: data.active_missions > 0 ? 'text-green-600' : 'text-muted-foreground',
      bgColor: data.active_missions > 0 ? 'bg-green-50 border-green-200' : 'bg-muted/30',
    },
    {
      label: 'Aircraft Status',
      value: `${data.aircraft_airworthy} / ${totalAircraft}`,
      sub: `${data.aircraft_in_maintenance} maint · ${data.aircraft_grounded} grounded`,
      color: data.aircraft_grounded > 0 ? 'text-red-600' : data.aircraft_in_maintenance > 0 ? 'text-amber-600' : 'text-green-600',
      bgColor: data.aircraft_grounded > 0 ? 'bg-red-50 border-red-200' : data.aircraft_in_maintenance > 0 ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200',
    },
    {
      label: 'Crew on Duty',
      value: data.crew_on_duty,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 border-blue-200',
    },
    {
      label: 'Flights Today',
      value: data.flights_today,
      color: data.flights_today > 0 ? 'text-green-600' : 'text-muted-foreground',
      bgColor: data.flights_today > 0 ? 'bg-green-50 border-green-200' : 'bg-muted/30',
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {statBoxes.map((s) => (
        <div
          key={s.label}
          className={`rounded-lg border p-4 ${s.bgColor}`}
        >
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {s.label}
          </p>
          <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          {s.sub && <p className="mt-0.5 text-xs text-muted-foreground">{s.sub}</p>}
        </div>
      ))}
    </div>
  )
}

function SystemStatsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-lg border p-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-2 h-8 w-16" />
        </div>
      ))}
    </div>
  )
}

// ── Card 2: Fleet Health ──────────────────────────────────────────────────

function FleetHealthCard({ data }: { data: FleetAircraft[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
            <th className="pb-2 pr-4 font-medium">Tail</th>
            <th className="pb-2 pr-4 font-medium">Type</th>
            <th className="pb-2 pr-4 font-medium">Status</th>
            <th className="pb-2 pr-4 font-medium">Mission Capability</th>
            <th className="pb-2 font-medium">Safe for Flight</th>
          </tr>
        </thead>
        <tbody>
          {data.map((ac) => (
            <tr key={ac.tail} className="border-b last:border-b-0 hover:bg-muted/30">
              <td className="py-2.5 pr-4 font-semibold">{ac.tail}</td>
              <td className="py-2.5 pr-4 text-muted-foreground">{ac.type}</td>
              <td className="py-2.5 pr-4">
                <Badge
                  variant={ac.status === 'active' ? 'success' : 'warning'}
                  className="capitalize"
                >
                  {ac.status.replace('_', ' ')}
                </Badge>
              </td>
              <td className="py-2.5 pr-4">
                <Badge variant={CAPABILITY_BADGE[ac.mission_capability]} className="capitalize">
                  {ac.mission_capability}
                </Badge>
              </td>
              <td className="py-2.5">
                {ac.safe_for_flight ? (
                  <span className="inline-flex items-center gap-1 text-green-600">
                    <Check className="h-4 w-4" /> Yes
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-red-600">
                    <X className="h-4 w-4" /> No
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FleetHealthSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-16" />
        </div>
      ))}
    </div>
  )
}

// ── Card 3: Parts & Upcoming Maintenance ──────────────────────────────────

function MaintenanceCard({ data }: { data: MaintenanceItem[] }) {
  return (
    <div className="space-y-4">
      {data.map((m) => (
        <div key={m.tail} className="rounded-lg border p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="font-semibold">{m.tail}</span>
            <span className="text-xs text-muted-foreground">{m.type}</span>
          </div>
          <div className="space-y-1.5">
            {m.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span>{item.description}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Due: {fmtDate(item.due_date)}</span>
                  <Badge variant={SEVERITY_BADGE[item.severity]} className="text-[10px] uppercase">
                    {item.severity}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
          {m.parts_needed.length > 0 && (
            <div className="mt-2 border-t pt-2">
              <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Parts Needed
              </p>
              <ul className="space-y-0.5">
                {m.parts_needed.map((p, idx) => (
                  <li key={idx} className="flex items-center gap-1 text-xs">
                    <Wrench className="h-3 w-3 text-amber-500" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function MaintenanceSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2].map((i) => (
        <div key={i} className="rounded-lg border p-3">
          <Skeleton className="mb-2 h-5 w-32" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="mt-1 h-4 w-3/4" />
        </div>
      ))}
    </div>
  )
}

// ── Card 4: Current & Upcoming Missions ───────────────────────────────────

function MissionsCard({ data }: { data: MissionItem[] }) {
  const navigate = useNavigate()

  return (
    <div className="space-y-2">
      {data.map((m) => {
        const badgeVariant = STATUS_BADGE[m.status] || 'secondary'
        return (
          <div
            key={m.id}
            className="flex cursor-pointer items-center justify-between rounded-md border p-3 text-sm transition-colors hover:bg-muted/50"
            onClick={() => navigate(`/missions/${m.id}`)}
          >
            <div className="flex flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <div className="min-w-0 flex-1">
                <p className="font-medium">{m.name}</p>
                <p className="text-xs text-muted-foreground">{m.route}</p>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Plane className="h-3 w-3" /> {m.aircraft}
                </span>
                <span className="hidden sm:inline">·</span>
                <span>{m.pic}</span>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="hidden text-xs text-muted-foreground sm:inline">
                {fmtTime(m.departure_time)}
              </span>
              <Badge variant={badgeVariant} className="capitalize">
                {m.status}
              </Badge>
            </div>
          </div>
        )
      })}
      {data.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No missions scheduled
        </p>
      )}
    </div>
  )
}

// ── Card 5: Financials Overview ───────────────────────────────────────────

function FinancialsCard({ data }: { data: FinancialData }) {
  const isPositive = data.mtd_variance >= 0
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border bg-green-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            MTD Revenue
          </p>
          <p className="mt-1 text-xl font-bold text-green-700">{fmtCurrency(data.mtd_revenue)}</p>
        </div>
        <div className="rounded-lg border bg-red-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            MTD Costs
          </p>
          <p className="mt-1 text-xl font-bold text-red-700">{fmtCurrency(data.mtd_costs)}</p>
        </div>
        <div className={`rounded-lg border p-3 ${isPositive ? 'bg-green-50' : 'bg-red-50'}`}>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            MTD Variance
          </p>
          <p className={`mt-1 text-xl font-bold ${isPositive ? 'text-green-700' : 'text-red-700'}`}>
            {isPositive ? '+' : ''}{fmtCurrency(data.mtd_variance)}
          </p>
          <p className="text-xs text-muted-foreground">
            {data.variance_pct >= 0 ? '+' : ''}{data.variance_pct.toFixed(1)}% margin
          </p>
        </div>
      </div>

      {data.per_aircraft.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Per-Aircraft Profitability
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-1.5 pr-3 font-medium">Tail</th>
                  <th className="pb-1.5 pr-3 font-medium">Revenue</th>
                  <th className="pb-1.5 pr-3 font-medium">Costs</th>
                  <th className="pb-1.5 font-medium">Margin</th>
                </tr>
              </thead>
              <tbody>
                {data.per_aircraft.map((ac) => (
                  <tr key={ac.tail} className="border-b last:border-b-0">
                    <td className="py-1.5 pr-3 font-medium">{ac.tail}</td>
                    <td className="py-1.5 pr-3 text-green-700">{fmtCurrency(ac.revenue)}</td>
                    <td className="py-1.5 pr-3 text-red-700">{fmtCurrency(ac.costs)}</td>
                    <td className={`py-1.5 font-medium ${ac.margin >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {ac.margin >= 0 ? '+' : ''}{fmtCurrency(ac.margin)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Card 6: Compliance Snapshot ───────────────────────────────────────────

function ComplianceCard({ data }: { data: ComplianceData }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-lg border p-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Expiring Documents
        </p>
        <div className="mt-1 flex items-center gap-2">
          <span className={`text-2xl font-bold ${data.expiring_documents > 0 ? 'text-amber-600' : 'text-green-600'}`}>
            {data.expiring_documents}
          </span>
          {data.expiring_documents > 0 && (
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          )}
        </div>
      </div>

      <div className="rounded-lg border p-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Crew Currency Issues
        </p>
        <div className="mt-1 flex items-center gap-2">
          <span className={`text-2xl font-bold ${data.crew_currency_issues > 0 ? 'text-amber-600' : 'text-green-600'}`}>
            {data.crew_currency_issues}
          </span>
          {data.crew_currency_issues > 0 && (
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          )}
        </div>
      </div>

      <div className="rounded-lg border p-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Open Gripe Items
        </p>
        <div className="mt-1 flex items-center gap-2">
          <span className={`text-2xl font-bold ${data.open_gripes > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {data.open_gripes}
          </span>
          {data.open_gripes > 0 && (
            <AlertOctagon className="h-4 w-4 text-red-500" />
          )}
        </div>
      </div>
    </div>
  )
}

// ── Card 7: Weather & Airspace ────────────────────────────────────────────

function WeatherCard({ data }: { data: WeatherData }) {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            IFR Airports
          </p>
          <p className={`mt-1 text-2xl font-bold ${data.ifr_airports.length > 0 ? 'text-amber-600' : 'text-green-600'}`}>
            {data.ifr_airports.length}
          </p>
          {data.ifr_airports.length > 0 && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {data.ifr_airports.join(', ')}
            </p>
          )}
        </div>
        <div className="rounded-lg border p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Active NOTAMs
          </p>
          <p className={`mt-1 text-2xl font-bold ${data.active_notams > 0 ? 'text-amber-600' : 'text-green-600'}`}>
            {data.active_notams}
          </p>
        </div>
        <div className="rounded-lg border p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            SIGMETs
          </p>
          <p className={`mt-1 text-2xl font-bold ${data.sigmets > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {data.sigmets}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────

export default function MorningBriefPage() {
  const { user } = useAuthContext()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const [visibility, setVisibility] = useState<Visibility | null>(null)
  const [systemStats, setSystemStats] = useState<SystemStatsData | null>(null)
  const [fleetHealth, setFleetHealth] = useState<FleetAircraft[] | null>(null)
  const [maintenance, setMaintenance] = useState<MaintenanceItem[] | null>(null)
  const [missions, setMissions] = useState<MissionItem[] | null>(null)
  const [financials, setFinancials] = useState<FinancialData | null>(null)
  const [compliance, setCompliance] = useState<ComplianceData | null>(null)
  const [weather, setWeather] = useState<WeatherData | null>(null)

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setError(false)

    // Use mock data directly — API endpoint shape needs refinement
    setVisibility({
      system_stats: true,
      fleet_health: true,
      parts_maintenance: true,
      missions: true,
      financials: true,
      compliance: true,
      weather: true,
    })
    setSystemStats(MOCK_SYSTEM_STATS)
    setFleetHealth(MOCK_FLEET)
    setMaintenance(MOCK_MAINTENANCE)
    setMissions(MOCK_MISSIONS)
    setFinancials(MOCK_FINANCIALS)
    setCompliance(MOCK_COMPLIANCE)
    setWeather(MOCK_WEATHER)
    setLastRefreshed(new Date())
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchDashboard()
  }, [fetchDashboard])

  // ── Top Bar ─────────────────────────────────────────────────────────────
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const timeStr = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })

  const role = user?.role ?? null

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Morning Brief</h1>
            {role && (
              <Badge variant={getRoleBadgeVariant(role)} className="ml-1 text-[10px] uppercase">
                {role.replace(/_/g, ' ')}
              </Badge>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" /> {dateStr}
            </span>
            <span className="hidden sm:inline">·</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" /> {timeStr}
            </span>
            {lastRefreshed && (
              <>
                <span className="hidden sm:inline">·</span>
                <span className="flex items-center gap-1">
                  Last refreshed: {lastRefreshed.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span>{user.display_name}</span>
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchDashboard}
            disabled={loading}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh All
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          Using demo data — backend API not available
        </div>
      )}

      {/* Cards */}
      {loading ? (
        <div className="space-y-6">
          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent>
              <SystemStatsSkeleton />
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <Skeleton className="h-5 w-36" />
            </CardHeader>
            <CardContent>
              <FleetHealthSkeleton />
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <Skeleton className="h-5 w-52" />
            </CardHeader>
            <CardContent>
              <MaintenanceSkeleton />
            </CardContent>
          </Card>
        </div>
      ) : (
        <>
          {/* Card 1: System Operating Stats */}
          {visibility?.system_stats && systemStats && (
            <CollapsibleCard title="System Operating Stats" icon={<Gauge className="h-4 w-4" />}>
              <SystemStatsCard data={systemStats} />
            </CollapsibleCard>
          )}

          {/* Card 2: Fleet Health */}
          {visibility?.fleet_health && fleetHealth && (
            <CollapsibleCard title="Fleet Health" icon={<Plane className="h-4 w-4" />}>
              <FleetHealthCard data={fleetHealth} />
            </CollapsibleCard>
          )}

          {/* Card 3: Parts & Upcoming Maintenance */}
          {visibility?.parts_maintenance && maintenance && (
            <CollapsibleCard title="Parts & Upcoming Maintenance" icon={<Wrench className="h-4 w-4" />}>
              <MaintenanceCard data={maintenance} />
            </CollapsibleCard>
          )}

          {/* Card 4: Current & Upcoming Missions */}
          {visibility?.missions && missions && (
            <CollapsibleCard title="Current & Upcoming Missions" icon={<MapPin className="h-4 w-4" />}>
              <MissionsCard data={missions} />
            </CollapsibleCard>
          )}

          {/* Card 5: Financials Overview (role-gated) */}
          {visibility?.financials && financials && role && canViewFinance(role) && (
            <CollapsibleCard title="Financials Overview" icon={<Wallet className="h-4 w-4" />}>
              <FinancialsCard data={financials} />
            </CollapsibleCard>
          )}

          {/* Card 6: Compliance Snapshot (role-gated) */}
          {visibility?.compliance && compliance && role && canViewCompliance(role) && (
            <CollapsibleCard title="Compliance Snapshot" icon={<ShieldCheck className="h-4 w-4" />}>
              <ComplianceCard data={compliance} />
            </CollapsibleCard>
          )}

          {/* Card 7: Weather & Airspace */}
          {visibility?.weather && weather && (
            <CollapsibleCard title="Weather & Airspace" icon={<CloudSun className="h-4 w-4" />}>
              <WeatherCard data={weather} />
            </CollapsibleCard>
          )}
        </>
      )}
    </div>
  )
}
