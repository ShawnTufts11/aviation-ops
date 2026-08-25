import { useState, useEffect, type FormEvent } from 'react'
import {
  Plus,
  FileText,
  PlaneTakeoff,
  PlaneLanding,
  MapPin,
  Clock,
  Fuel,
  CloudSun,
  AlertTriangle,
  Wrench,
  ShieldCheck,
  PenLine,
  UserCheck,
  ArrowLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Printer,
  FileSpreadsheet,
  Weight,
  RefreshCw,
  DollarSign,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import api from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

interface RouteLeg {
  leg: number
  origin: string
  destination: string
  alt: string
  distance_nm: number
  altitude: string
  wind: string
  time_enroute: string
  remarks: string
}

interface Notam {
  id: string
  airport: string
  code: string
  description: string
  severity: 'info' | 'caution' | 'warning'
  start_date: string
  end_date: string
}

interface FuelPlan {
  fuel_type: string
  ramp_fuel_lbs: number
  taxi_fuel_lbs: number
  trip_fuel_lbs: number
  reserve_fuel_lbs: number
  alternate_fuel_lbs: number
  final_reserve_lbs: number
  total_required_lbs: number
  total_onboard_lbs: number
}

interface HotZoneAssessment {
  threat_level: 'none' | 'low' | 'medium' | 'high'
  assessed_by: string
  assessment_date: string
  notes: string
  mitigation_steps: string[]
}

interface Gripe {
  id: string
  description: string
  severity: 'minor' | 'major' | 'critical'
  status: 'open' | 'deferred' | 'resolved'
  date_logged: string
  mechanic_notes: string
}

interface WeatherBrief {
  departure_metar: string
  departure_taf: string
  destination_metar: string
  destination_taf: string
  alternate_metar: string
  alternate_taf: string
}

interface FlightRelease {
  id: string
  title: string
  status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'cancelled'
  created_at: string
  updated_at: string

  // Flight Identity
  flight_number: string
  mission_name: string
  departure_airport: string
  arrival_airport: string
  alternate_airport: string
  aircraft_tail: string
  aircraft_type: string
  scheduled_departure: string
  scheduled_arrival: string

  // Crew & Duty
  pilot_in_command: string
  second_in_command: string
  crew_duty_time: string
  crew_rest_period: string
  crew_notes: string

  // Route Nav Log
  route_legs: RouteLeg[]

  // Weather Brief
  weather_brief: WeatherBrief
  weather_source: string
  weather_brief_time: string
  weather_overview: string

  // NOTAMs
  notams: Notam[]

  // Fuel Plan
  fuel_plan: FuelPlan

  // Hot-Zone Assessment
  hot_zone_assessment: HotZoneAssessment

  // Maintenance Control Safe-for-Flight
  maintenance_release: string
  maintenance_engineer: string
  maintenance_date: string
  maintenance_notes: string

  // Gripes
  gripes: Gripe[]

  // Authorizations
  created_by: string
  authorized_by: string | null
  authorization_date: string | null
  release_signature: string | null
}

// ── Status config ──────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'bg-muted text-muted-foreground' },
  submitted: { label: 'Submitted', color: 'bg-blue-500/10 text-blue-500' },
  approved: { label: 'Approved', color: 'bg-green-500/10 text-green-500' },
  rejected: { label: 'Rejected', color: 'bg-red-500/10 text-red-500' },
  cancelled: { label: 'Cancelled', color: 'bg-amber-500/10 text-amber-500' },
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtDate(d: string | null) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmtTime(d: string | null) {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

// ── METAR Parser ────────────────────────────────────────────────────────────

interface ParsedMetar {
  wind: string
  visibility: string
  ceiling: string
  ceiling_ft: number
  flightCategory: 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'N/A'
  temp: string
  altimeter: string
}

function parseMetar(metar: string): ParsedMetar {
  const empty: ParsedMetar = {
    wind: '—', visibility: '—', ceiling: '—', ceiling_ft: 99999,
    flightCategory: 'N/A', temp: '—', altimeter: '—',
  }
  if (!metar || metar.trim() === '') return empty

  // Wind: 5-digit direction + speed, optional G gust, KT/MPS
  const windMatch = metar.match(/(\d{3})(\d{2})G?(\d{0,2})(?:KT|MPS)/)
  const wind = windMatch
    ? `${windMatch[1]}°/${windMatch[2]}${windMatch[3] ? `G${windMatch[3]}` : ''}kt`
    : '—'

  // Visibility: either 4-digit (metric) or number + SM
  let visibility = '—'
  const visSmMatch = metar.match(/(\d+\s?\d?\/?\d*)SM/)
  const visMetricMatch = metar.match(/\s(\d{4})\s/)
  if (visSmMatch) {
    visibility = visSmMatch[1] + ' SM'
  } else if (visMetricMatch) {
    const v = parseInt(visMetricMatch[1])
    visibility = v >= 9999 ? '10+ km (CAVOK)' : `${v} m`
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
  const visValue = (() => {
    if (visSmMatch) {
      const v = visSmMatch[1]
      if (v.includes('/')) {
        const [num, den] = v.split(/\s+/).filter(Boolean).join(' ').split('/')
        return parseFloat(num) / parseFloat(den)
      }
      return parseFloat(v)
    }
    if (visMetricMatch) {
      return parseInt(visMetricMatch[1]) >= 9999 ? 10 : parseInt(visMetricMatch[1]) / 1000
    }
    // Check for CAVOK
    if (metar.includes('CAVOK')) return 10
    return 0
  })()

  if (ceiling_ft >= 3000 && visValue >= 5) flightCategory = 'VFR'
  else if (ceiling_ft >= 1000 && visValue >= 3) flightCategory = 'MVFR'
  else if (ceiling_ft >= 500 && visValue >= 1) flightCategory = 'IFR'
  else if (ceiling_ft < 99999) flightCategory = 'LIFR'

  // Temperature / dewpoint
  const tempMatch = metar.match(/\s(M?\d{2})\/(M?\d{2})\s/)
  const temp = tempMatch
    ? `${tempMatch[1].replace('M', '-')}° / ${tempMatch[2].replace('M', '-')}°`
    : '—'

  // Altimeter
  let altimeter = '—'
  const qnhMatch = metar.match(/Q(\d{4})/)
  if (qnhMatch) altimeter = `${qnhMatch[1]} hPa`
  else {
    const altMatch = metar.match(/A(\d{4})/)
    if (altMatch) altimeter = `${altMatch[1].slice(0, 2)}.${altMatch[1].slice(2)} inHg`
  }

  return { wind, visibility, ceiling, ceiling_ft, flightCategory, temp, altimeter }
}

const FC_COLORS: Record<string, string> = {
  'VFR': 'text-green-600 bg-green-100 dark:bg-green-900/20 dark:text-green-400',
  'MVFR': 'text-blue-600 bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400',
  'IFR': 'text-red-600 bg-red-100 dark:bg-red-900/20 dark:text-red-400',
  'LIFR': 'text-purple-600 bg-purple-100 dark:bg-purple-900/20 dark:text-purple-400',
}

function MetarCard({ label, metar, taf }: { label: string; metar: string; taf: string }) {
  const parsed = parseMetar(metar)
  const hasData = metar.trim() !== ''

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-sm">
          <span>{label}</span>
          {hasData && (
            <Badge variant="outline" className={`font-mono text-xs ${FC_COLORS[parsed.flightCategory] || ''}`}>
              {parsed.flightCategory}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {!hasData ? (
          <p className="text-xs text-muted-foreground italic">No weather data available.</p>
        ) : (
          <>
            <div className="rounded-md bg-muted/20 p-2 font-mono text-xs leading-relaxed break-all">
              {metar}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <span className="text-muted-foreground">Wind:</span>
              <span className="font-medium">{parsed.wind}</span>
              <span className="text-muted-foreground">Visibility:</span>
              <span className="font-medium">{parsed.visibility}</span>
              <span className="text-muted-foreground">Ceiling:</span>
              <span className="font-medium">{parsed.ceiling}</span>
              <span className="text-muted-foreground">Temp/Dew:</span>
              <span className="font-medium">{parsed.temp}</span>
              <span className="text-muted-foreground">Altimeter:</span>
              <span className="font-medium">{parsed.altimeter}</span>
            </div>
            {taf.trim() && (
              <div className="mt-2">
                <p className="mb-1 text-xs font-medium text-muted-foreground">TAF</p>
                <div className="rounded-md bg-muted/10 p-2 font-mono text-xs leading-relaxed break-all">
                  {taf}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ── Mock data ──────────────────────────────────────────────────────────────

const CARIBBEAN_LEGS: RouteLeg[] = [
  { leg: 1, origin: 'MYNN', destination: 'KMIA', alt: 'KFLL', distance_nm: 164, altitude: 'FL180', wind: '270/15', time_enroute: '0:52', remarks: 'Overwater — life vests required' },
  { leg: 2, origin: 'KMIA', destination: 'MMUN', alt: 'MMCZ', distance_nm: 477, altitude: 'FL240', wind: '280/20', time_enroute: '1:35', remarks: 'ADIZ crossing — squawk discrete' },
  { leg: 3, origin: 'MMUN', destination: 'MTPP', alt: 'MTPP', distance_nm: 1024, altitude: 'FL280', wind: '100/12', time_enroute: '2:50', remarks: 'Oceanic — CPDLC req' },
  { leg: 4, origin: 'MTPP', destination: 'MUHA', alt: 'MUHA', distance_nm: 790, altitude: 'FL260', wind: '080/18', time_enroute: '2:15', remarks: 'Havana FIR — prior coord' },
  { leg: 5, origin: 'MUHA', destination: 'MDPC', alt: 'MDPC', distance_nm: 340, altitude: 'FL200', wind: '090/14', time_enroute: '1:05', remarks: 'Punta Cana approach' },
  { leg: 6, origin: 'MDPC', destination: 'MYNN', alt: 'MYNN', distance_nm: 690, altitude: 'FL240', wind: '270/10', time_enroute: '2:00', remarks: 'Return overwater' },
]

const MOCK_NOTAMS: Notam[] = [
  { id: 'n1', airport: 'MYNN', code: 'MYNN 04/012', description: 'RWY 14/32 CLSD WIP 1000-1800Z', severity: 'warning', start_date: '2026-07-16T08:00:00Z', end_date: '2026-07-17T18:00:00Z' },
  { id: 'n2', airport: 'KMIA', code: 'KMIA 04/008', description: 'ILS 09L U/S — LOC only', severity: 'caution', start_date: '2026-07-15T12:00:00Z', end_date: '2026-07-18T23:59:00Z' },
  { id: 'n3', airport: 'MMUN', code: 'MMUN 04/003', description: 'APRON B N closed — construction', severity: 'info', start_date: '2026-07-10T00:00:00Z', end_date: '2026-07-31T23:59:00Z' },
  { id: 'n4', airport: 'MTPP', code: 'MTPP 03/015', description: 'VOR/DME 115.7 U/S', severity: 'caution', start_date: '2026-07-14T06:00:00Z', end_date: '2026-07-20T23:59:00Z' },
  { id: 'n5', airport: 'MUHA', code: 'MUHA 04/001', description: 'Airspace RESTRICTED B20 active 0800-2000Z', severity: 'warning', start_date: '2026-07-16T08:00:00Z', end_date: '2026-07-16T20:00:00Z' },
]

const MOCK_FUEL_PLAN: FuelPlan = {
  fuel_type: 'Jet A-1',
  ramp_fuel_lbs: 16500,
  taxi_fuel_lbs: 300,
  trip_fuel_lbs: 11200,
  reserve_fuel_lbs: 2400,
  alternate_fuel_lbs: 1200,
  final_reserve_lbs: 800,
  total_required_lbs: 15900,
  total_onboard_lbs: 16500,
}

const MOCK_HOT_ZONE: HotZoneAssessment = {
  threat_level: 'low',
  assessed_by: 'Shawn M. (Ops Manager)',
  assessment_date: '2026-07-16T06:00:00Z',
  notes: 'Caribbean route passes near Cuban airspace. Standard overwater procedures apply. No active military exercises in forecast region.',
  mitigation_steps: [
    'Monitor HF/CPDLC on Oceanic sectors',
    'File ICAO flight plan with 2 alternates',
    'Verify life vests & rafts for all crew/pax',
    'Brief AIT (Anti-Illicit Trafficking) procedures for ADIZ crossings',
    'SATCOM check prior to departure',
  ],
}

const MOCK_GRIPES: Gripe[] = [
  { id: 'g1', description: 'Cabin reading light #3 inop', severity: 'minor', status: 'deferred', date_logged: '2026-07-14T14:00:00Z', mechanic_notes: 'Deferred per MEL 33-01 — bulb on order' },
  { id: 'g2', description: 'RH fuel gauge intermittent', severity: 'major', status: 'open', date_logged: '2026-07-15T09:00:00Z', mechanic_notes: 'Investigating — ground test scheduled' },
]

const DEMO_MISSION: FlightRelease = {
  id: 'rel-001',
  title: 'Caribbean Loop Challenge — OP-001',
  status: 'draft',
  created_at: '2026-07-16T06:00:00Z',
  updated_at: '2026-07-16T06:30:00Z',

  flight_number: 'PRC-101',
  mission_name: 'Caribbean Loop Challenge',
  departure_airport: 'MYNN',
  arrival_airport: 'MYNN',
  alternate_airport: 'KMIA',
  aircraft_tail: 'N701PR',
  aircraft_type: 'Cessna Citation CJ4',
  scheduled_departure: '2026-07-17T09:00:00Z',
  scheduled_arrival: '2026-07-18T01:00:00Z',

  pilot_in_command: 'Capt. Jack D.',
  second_in_command: 'FO Sarah K.',
  crew_duty_time: '14:00',
  crew_rest_period: '12:00 prior',
  crew_notes: 'Both crew qualified for overwater operations. Current on oceanic CRM training.',

  route_legs: CARIBBEAN_LEGS,

  weather_brief: {
    departure_metar: 'MYNN 161500Z 28012G18KT 9999 FEW025 SCT045 30/22 Q1015 NOSIG',
    departure_taf: 'TAF MYNN 161100Z 1612/1712 27012KT 9999 SCT025 PROB30 1618/1622 TSRA FEW023CB BKN040',
    destination_metar: 'MYNN 161500Z 28012G18KT 9999 FEW025 SCT045 30/22 Q1015 NOSIG',
    destination_taf: 'TAF MYNN 161100Z 1612/1712 27012KT 9999 SCT025 PROB30 1618/1622 TSRA FEW023CB BKN040',
    alternate_metar: 'KMIA 161453Z 25010KT 10SM FEW030 SCT250 31/23 A3003',
    alternate_taf: 'TAF KMIA 161120Z 1612/1718 24008KT P6SM SCT030 FM162000 26012G18KT P6SM SCT050',
  },
  weather_source: 'NOAA / ADDS',
  weather_brief_time: '2026-07-16T07:00:00Z',
  weather_overview: 'VFR conditions at all airports. TS possible MUHA PM. Winds aloft 270@15-20kt at FL240. Isolated convection near Bahamas ridge — recommend departure before 13Z.',

  notams: MOCK_NOTAMS,

  fuel_plan: MOCK_FUEL_PLAN,

  hot_zone_assessment: MOCK_HOT_ZONE,

  maintenance_release: 'R-2026-0716-01',
  maintenance_engineer: 'Tom R. (MX-3)',
  maintenance_date: '2026-07-16T05:00:00Z',
  maintenance_notes: 'Aircraft signed-off for IFR / Extended Overwater / Night. All MEL items within limits. Oil changed at 14.2 hours (12.1 remaining).',

  gripes: MOCK_GRIPES,

  created_by: 'Shawn M.',
  authorized_by: null,
  authorization_date: null,
  release_signature: null,
}

// ── Weight & Balance mock data ──────────────────────────────────────────────

interface WbPerLeg {
  leg: number
  origin: string
  destination: string
  total_weight_lbs: number
  mtow_lbs: number
  cg_position: string
  takeoff_distance_ft: number
  landing_distance_ft: number
  status: 'ok' | 'warning' | 'over_limit'
}

const MOCK_WB_LEGS: WbPerLeg[] = [
  { leg: 1, origin: 'MYNN', destination: 'KMIA', total_weight_lbs: 9650, mtow_lbs: 10300, cg_position: '28.3% MAC', takeoff_distance_ft: 3250, landing_distance_ft: 2950, status: 'ok' },
  { leg: 2, origin: 'KMIA', destination: 'MMUN', total_weight_lbs: 9100, mtow_lbs: 10300, cg_position: '27.8% MAC', takeoff_distance_ft: 3100, landing_distance_ft: 2800, status: 'ok' },
  { leg: 3, origin: 'MMUN', destination: 'MTPP', total_weight_lbs: 8450, mtow_lbs: 10300, cg_position: '26.5% MAC', takeoff_distance_ft: 2900, landing_distance_ft: 2650, status: 'ok' },
  { leg: 4, origin: 'MTPP', destination: 'MUHA', total_weight_lbs: 9300, mtow_lbs: 10300, cg_position: '28.1% MAC', takeoff_distance_ft: 3350, landing_distance_ft: 3000, status: 'warning' },
  { leg: 5, origin: 'MUHA', destination: 'MDPC', total_weight_lbs: 8800, mtow_lbs: 10300, cg_position: '27.0% MAC', takeoff_distance_ft: 3050, landing_distance_ft: 2750, status: 'ok' },
  { leg: 6, origin: 'MDPC', destination: 'MYNN', total_weight_lbs: 7800, mtow_lbs: 10300, cg_position: '25.2% MAC', takeoff_distance_ft: 2700, landing_distance_ft: 2500, status: 'ok' },
]

// ── Crew Duty mock data ────────────────────────────────────────────────────

interface CrewDutyCheck {
  name: string
  role: 'PIC' | 'SIC'
  duty_used_hrs: number
  duty_remaining_hrs: number
  rest_period_hrs: number
  pass: boolean
  violations: string[]
}

const MOCK_CREW_DUTY: CrewDutyCheck[] = [
  { name: 'Capt. Jack D.', role: 'PIC', duty_used_hrs: 6.5, duty_remaining_hrs: 7.5, rest_period_hrs: 12.0, pass: true, violations: [] },
  { name: 'FO Sarah K.', role: 'SIC', duty_used_hrs: 5.0, duty_remaining_hrs: 9.0, rest_period_hrs: 12.0, pass: true, violations: [] },
]

// ── Landing Costs mock data ─────────────────────────────────────────────────

interface LandingCostLegLocal {
  leg: number
  origin: string
  destination: string
  landing_fee_usd: number
  overnight_parking_usd: number
  handling_fee_usd: number
  customs_fee_usd: number
  overflight_permit_cost_usd: number
  payment_type: 'cash_only' | 'credit' | 'mixed'
  estimated_cash_needed: number
}

const MOCK_LANDING_COST_LEGS: LandingCostLegLocal[] = [
  { leg: 1, origin: 'MYNN', destination: 'KMIA', landing_fee_usd: 150, overnight_parking_usd: 75, handling_fee_usd: 200, customs_fee_usd: 0, overflight_permit_cost_usd: 0, payment_type: 'credit', estimated_cash_needed: 425 },
  { leg: 2, origin: 'KMIA', destination: 'MMUN', landing_fee_usd: 250, overnight_parking_usd: 0, handling_fee_usd: 180, customs_fee_usd: 50, overflight_permit_cost_usd: 120, payment_type: 'mixed', estimated_cash_needed: 600 },
  { leg: 3, origin: 'MMUN', destination: 'MTPP', landing_fee_usd: 300, overnight_parking_usd: 0, handling_fee_usd: 220, customs_fee_usd: 60, overflight_permit_cost_usd: 150, payment_type: 'cash_only', estimated_cash_needed: 730 },
  { leg: 4, origin: 'MTPP', destination: 'MUHA', landing_fee_usd: 200, overnight_parking_usd: 0, handling_fee_usd: 150, customs_fee_usd: 40, overflight_permit_cost_usd: 80, payment_type: 'cash_only', estimated_cash_needed: 470 },
  { leg: 5, origin: 'MUHA', destination: 'MDPC', landing_fee_usd: 180, overnight_parking_usd: 0, handling_fee_usd: 160, customs_fee_usd: 30, overflight_permit_cost_usd: 0, payment_type: 'mixed', estimated_cash_needed: 370 },
  { leg: 6, origin: 'MDPC', destination: 'MYNN', landing_fee_usd: 220, overnight_parking_usd: 100, handling_fee_usd: 190, customs_fee_usd: 0, overflight_permit_cost_usd: 0, payment_type: 'credit', estimated_cash_needed: 510 },
]

// ── Section Sub-components ─────────────────────────────────────────────────

function SectionCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-border/30 py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '—'}</span>
    </div>
  )
}

function GripeBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    minor: 'bg-blue-500/10 text-blue-500',
    major: 'bg-amber-500/10 text-amber-500',
    critical: 'bg-red-500/10 text-red-500',
  }
  return <Badge variant="outline" className={colors[severity] || ''}>{severity}</Badge>
}

// ── Print Document ─────────────────────────────────────────────────────────

function PrintReleaseDocument({ release }: { release: FlightRelease }) {
  const cfg = STATUS_CONFIG[release.status] || { label: release.status, color: '' }
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  })

  const SectionHeader = ({ title }: { title: string }) => (
    <div className="print-section-header">
      <h3 className="print-section-title">{title}</h3>
      <hr className="print-section-rule" />
    </div>
  )

  const Field = ({ label, value }: { label: string; value: string }) => (
    <div className="print-field-row">
      <span className="print-field-label">{label}</span>
      <span className="print-field-value">{value || '—'}</span>
    </div>
  )

  const severityLabel: Record<string, string> = {
    none: 'None', low: 'Low', medium: 'Medium', high: 'High',
  }

  // ── Raw METAR text helper ──
  const MetarDisplay = ({ metar, taf, label }: { metar: string; taf: string; label: string }) => (
    <div className="print-metar-block">
      <p className="print-metar-label">{label}</p>
      {metar.trim() ? (
        <div className="print-raw-weather">
          <p className="print-raw-label">METAR</p>
          <pre className="print-raw-text">{metar}</pre>
        </div>
      ) : (
        <p className="print-raw-missing">Live weather not fetched</p>
      )}
      {taf.trim() && (
        <div className="print-raw-weather">
          <p className="print-raw-label">TAF</p>
          <pre className="print-raw-text">{taf}</pre>
        </div>
      )}
    </div>
  )

  return (
    <div className="print-release-document print-only">
      {/* ── Formal Header ── */}
      <div className="print-header-bar">
        <div className="print-header-left">
          <p className="print-header-org">PARARIG AVIATION OPERATIONS</p>
          <h2 className="print-header-title">FLIGHT RELEASE {release.flight_number}</h2>
          <p className="print-header-subtitle">{release.title}</p>
        </div>
        <div className="print-header-right">
          <span className={`print-status-badge ${cfg.color}`}>{cfg.label}</span>
        </div>
      </div>

      {/* ── Summary Bar ── */}
      <div className="print-summary-bar">
        <span>{release.departure_airport} → {release.arrival_airport}</span>
        <span>·</span>
        <span>{release.aircraft_tail} ({release.aircraft_type})</span>
        <span>·</span>
        <span>PIC: {release.pilot_in_command}</span>
        <span>·</span>
        <span>Dep: {fmtTime(release.scheduled_departure)}</span>
        <span>·</span>
        <span>Alt: {release.alternate_airport}</span>
      </div>

      {/* ── 1. Flight Identity ── */}
      <SectionHeader title="1. FLIGHT IDENTITY" />
      <div className="print-grid-2col">
        <div>
          <Field label="Flight Number" value={release.flight_number} />
          <Field label="Mission Name" value={release.mission_name} />
          <Field label="Departure Airport" value={release.departure_airport} />
          <Field label="Arrival Airport" value={release.arrival_airport} />
          <Field label="Alternate Airport" value={release.alternate_airport} />
        </div>
        <div>
          <Field label="Aircraft Tail" value={release.aircraft_tail} />
          <Field label="Aircraft Type" value={release.aircraft_type} />
          <Field label="Scheduled Departure" value={fmtDate(release.scheduled_departure)} />
          <Field label="Scheduled Arrival" value={fmtDate(release.scheduled_arrival)} />
        </div>
      </div>

      {/* ── 2. Crew & Duty ── */}
      <SectionHeader title="2. CREW & DUTY" />
      <div className="print-grid-2col">
        <div>
          <Field label="Pilot in Command" value={release.pilot_in_command} />
          <Field label="Second in Command" value={release.second_in_command} />
        </div>
        <div>
          <Field label="Crew Duty Time" value={release.crew_duty_time} />
          <Field label="Crew Rest Period" value={release.crew_rest_period} />
        </div>
      </div>
      {release.crew_notes && (
        <div className="print-note-box">
          <span className="print-note-label">Crew Notes: </span>
          {release.crew_notes}
        </div>
      )}

      {/* ── 3. Route / Nav Log ── */}
      <SectionHeader title="3. ROUTE / NAV LOG" />
      <table className="print-table">
        <thead>
          <tr>
            <th>Leg</th>
            <th>Origin</th>
            <th>Dest</th>
            <th>Alt</th>
            <th>Dist (nm)</th>
            <th>Alt</th>
            <th>Wind</th>
            <th>ETE</th>
            <th>Remarks</th>
          </tr>
        </thead>
        <tbody>
          {release.route_legs.map((leg) => (
            <tr key={leg.leg}>
              <td className="print-mono">{leg.leg}</td>
              <td className="print-bold">{leg.origin}</td>
              <td className="print-bold">{leg.destination}</td>
              <td>{leg.alt}</td>
              <td className="print-mono">{leg.distance_nm}</td>
              <td className="print-mono">{leg.altitude}</td>
              <td className="print-mono">{leg.wind}</td>
              <td className="print-mono">{leg.time_enroute}</td>
              <td className="print-muted">{leg.remarks}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="print-total-row">
            <td colSpan={4} className="print-total-label">Totals:</td>
            <td className="print-mono">{release.route_legs.reduce((s, l) => s + l.distance_nm, 0)}</td>
            <td colSpan={3} className="print-mono">
              {release.route_legs.reduce((s, l) => {
                const [m, sec] = l.time_enroute.split(':').map(Number)
                return s + m + sec / 60
              }, 0).toFixed(1)} hrs
            </td>
            <td />
          </tr>
        </tfoot>
      </table>

      {/* ── 4. Weather Brief ── */}
      <SectionHeader title="4. WEATHER BRIEF" />
      <div className="print-grid-2col">
        <Field label="Source" value={release.weather_source} />
        <Field label="Briefed At" value={fmtDate(release.weather_brief_time)} />
      </div>
      <div className="print-note-box">
        <p className="print-note-label">Weather Overview</p>
        <p className="print-overview-text">{release.weather_overview}</p>
      </div>
      <div className="print-metar-grid">
        <MetarDisplay
          label={`Departure (${release.departure_airport})`}
          metar={release.weather_brief.departure_metar}
          taf={release.weather_brief.departure_taf}
        />
        <MetarDisplay
          label={`Destination (${release.arrival_airport})`}
          metar={release.weather_brief.destination_metar}
          taf={release.weather_brief.destination_taf}
        />
        <MetarDisplay
          label={`Alternate (${release.alternate_airport})`}
          metar={release.weather_brief.alternate_metar}
          taf={release.weather_brief.alternate_taf}
        />
      </div>

      {/* ── 5. NOTAMs ── */}
      <SectionHeader title="5. NOTAMS" />
      {release.notams.length === 0 ? (
        <p className="print-empty-text">No NOTAMs issued.</p>
      ) : (
        <div className="print-notam-list">
          {release.notams.map((notam) => (
            <div key={notam.id} className="print-notam-item">
              <div className="print-notam-header">
                <span className="print-notam-code">{notam.code}</span>
                <span className={`print-notam-severity print-notam-${notam.severity}`}>{notam.severity}</span>
                <span className="print-notam-airport">{notam.airport}</span>
              </div>
              <p className="print-notam-desc">{notam.description}</p>
              <p className="print-notam-dates">{fmtDate(notam.start_date)} – {fmtDate(notam.end_date)}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── 6. Fuel Plan ── */}
      <SectionHeader title="6. FUEL PLAN" />
      <Field label="Fuel Type" value={release.fuel_plan.fuel_type} />
      <div className="print-grid-2col">
        <div>
          <Field label="Ramp Fuel" value={`${release.fuel_plan.ramp_fuel_lbs.toLocaleString()} lbs`} />
          <Field label="Taxi Fuel" value={`${release.fuel_plan.taxi_fuel_lbs.toLocaleString()} lbs`} />
          <Field label="Trip Fuel" value={`${release.fuel_plan.trip_fuel_lbs.toLocaleString()} lbs`} />
          <Field label="Reserve Fuel" value={`${release.fuel_plan.reserve_fuel_lbs.toLocaleString()} lbs`} />
        </div>
        <div>
          <Field label="Alternate Fuel" value={`${release.fuel_plan.alternate_fuel_lbs.toLocaleString()} lbs`} />
          <Field label="Final Reserve" value={`${release.fuel_plan.final_reserve_lbs.toLocaleString()} lbs`} />
          <Field label="Total Required" value={`${release.fuel_plan.total_required_lbs.toLocaleString()} lbs`} />
          <Field label="Total Onboard" value={`${release.fuel_plan.total_onboard_lbs.toLocaleString()} lbs`} />
        </div>
      </div>
      <div className="print-fuel-balance">
        <span>Fuel Balance</span>
        <span className={release.fuel_plan.total_onboard_lbs >= release.fuel_plan.total_required_lbs ? 'print-balance-ok' : 'print-balance-fail'}>
          +{(release.fuel_plan.total_onboard_lbs - release.fuel_plan.total_required_lbs).toLocaleString()} lbs
          {release.fuel_plan.total_onboard_lbs >= release.fuel_plan.total_required_lbs ? ' ✅' : ' ⚠️'}
        </span>
      </div>

      {/* ── 7. Hot-Zone Assessment ── */}
      <SectionHeader title="7. HOT-ZONE ASSESSMENT" />
      <div className="print-grid-2col">
        <Field label="Threat Level" value={(severityLabel[release.hot_zone_assessment.threat_level] || release.hot_zone_assessment.threat_level).toUpperCase()} />
        <Field label="Assessed By" value={release.hot_zone_assessment.assessed_by} />
        <Field label="Assessment Date" value={fmtDate(release.hot_zone_assessment.assessment_date)} />
      </div>
      <div className="print-note-box">
        <p className="print-note-label">Assessment Notes</p>
        <p className="print-overview-text">{release.hot_zone_assessment.notes}</p>
      </div>
      {release.hot_zone_assessment.mitigation_steps.length > 0 && (
        <div className="print-mitigation">
          <p className="print-note-label">Mitigation Steps</p>
          <ol className="print-mitigation-list">
            {release.hot_zone_assessment.mitigation_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {/* ── 8. Maintenance Control Safe-for-Flight ── */}
      <SectionHeader title="8. MAINTENANCE CONTROL — SAFE-FOR-FLIGHT" />
      <div className="print-grid-2col">
        <Field label="Maintenance Release" value={release.maintenance_release} />
        <Field label="Engineer" value={release.maintenance_engineer} />
        <Field label="Date Signed" value={fmtDate(release.maintenance_date)} />
      </div>
      {release.maintenance_notes && (
        <div className="print-mx-safe">
          <p className="print-safe-label">SAFE FOR FLIGHT</p>
          <p className="print-overview-text">{release.maintenance_notes}</p>
        </div>
      )}

      {/* ── 9. Gripes (Squawks) ── */}
      <SectionHeader title="9. GRIPES (SQUAWKS)" />
      {release.gripes.length === 0 ? (
        <p className="print-empty-text">No open gripes.</p>
      ) : (
        <div className="print-gripe-list">
          {release.gripes.map((gripe) => (
            <div key={gripe.id} className="print-gripe-item">
              <div className="print-gripe-header">
                <span className="print-gripe-desc">{gripe.description}</span>
                <span className="print-gripe-badge">{gripe.severity}</span>
              </div>
              <p className="print-gripe-meta">
                Logged: {fmtDate(gripe.date_logged)} · Status: {gripe.status}
              </p>
              {gripe.mechanic_notes && (
                <p className="print-gripe-mx">MX Notes: {gripe.mechanic_notes}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── 10. Authorizations & Signatures ── */}
      <SectionHeader title="10. AUTHORIZATIONS & SIGNATURES" />
      <div className="print-grid-2col">
        <Field label="Created By" value={release.created_by} />
        <Field label="Authorized By" value={release.authorized_by || '—'} />
        <Field label="Authorization Date" value={release.authorization_date ? fmtDate(release.authorization_date) : '—'} />
      </div>

      {/* Three Signature Blocks */}
      <div className="print-signature-section">
        <div className="print-signature-block">
          <p className="print-sig-label">PREPARED BY (Dispatch)</p>
          <div className="print-sig-line" />
          <p className="print-sig-meta">{release.created_by} — {fmtDate(release.created_at)}</p>
        </div>
        <div className="print-signature-block">
          <p className="print-sig-label">REVIEWED BY (Pilot in Command)</p>
          <div className="print-sig-line" />
          <p className="print-sig-meta">{release.pilot_in_command} — Signature: ___________________</p>
        </div>
        <div className="print-signature-block">
          <p className="print-sig-label">AUTHORIZED BY (Operations)</p>
          <div className="print-sig-line" />
          <p className="print-sig-meta">
            {release.authorized_by
              ? `${release.authorized_by} — ${fmtDate(release.authorization_date)}`
              : 'Pending authorization'}
          </p>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="print-footer">
        <hr className="print-footer-rule" />
        <div className="print-footer-text">
          <span>Generated {dateStr} — Revision 1</span>
          <span className="print-footer-disclaimer">
            This document is electronically generated and does not require a physical signature
            to be valid for operational purposes.
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Detail View ────────────────────────────────────────────────────────────

function ReleaseDetailView({
  release,
  onBack,
  onApprove,
}: {
  release: FlightRelease
  onBack: () => void
  onApprove: () => void
}) {
  const cfg = STATUS_CONFIG[release.status] || { label: release.status, color: '' }
  const isDraft = release.status === 'draft'
  const isSubmitted = release.status === 'submitted'

  const [fetchingWeather, setFetchingWeather] = useState(false)
  const [wbExpanded, setWbExpanded] = useState(false)
  const [dutyExpanded, setDutyExpanded] = useState(false)
  const [refreshingWb, setRefreshingWb] = useState(false)
  const [refreshingDuty, setRefreshingDuty] = useState(false)
  const [wbLegs, setWbLegs] = useState<WbPerLeg[]>(MOCK_WB_LEGS)
  const [crewDutyChecks, setCrewDutyChecks] = useState<CrewDutyCheck[]>(MOCK_CREW_DUTY)

  // Landing Costs state
  const [costsExpanded, setCostsExpanded] = useState(false)
  const [refreshingCosts, setRefreshingCosts] = useState(false)
  const [landingCostLegs, setLandingCostLegs] = useState<LandingCostLegLocal[]>(MOCK_LANDING_COST_LEGS)

  // Preflight Checklist state
  const [preflightPic, setPreflightPic] = useState('')
  const [preflightFunds, setPreflightFunds] = useState(false)
  const [preflightPayment, setPreflightPayment] = useState(false)
  const [preflightSaved, setPreflightSaved] = useState(false)
  const [preflightDate] = useState(new Date().toISOString().slice(0, 10))

  const handleRefreshWb = async () => {
    setRefreshingWb(true)
    try {
      const res = await api.post('/api/v1/routes/plan', {
        release_id: release.id,
      })
      if (res.data?.weight_balance) {
        setWbLegs(res.data.weight_balance as WbPerLeg[])
      }
    } catch {
      // API not available — keep mock data
    }
    setRefreshingWb(false)
  }

  const handleRefreshDuty = async () => {
    setRefreshingDuty(true)
    try {
      const res = await api.post('/api/v1/routes/plan', {
        release_id: release.id,
      })
      if (res.data?.crew_duty) {
        setCrewDutyChecks(res.data.crew_duty as CrewDutyCheck[])
      }
    } catch {
      // API not available — keep mock data
    }
    setRefreshingDuty(false)
  }

  const handleRefreshCosts = async () => {
    setRefreshingCosts(true)
    try {
      const res = await api.post('/api/v1/routes/plan', {
        release_id: release.id,
      })
      if (res.data?.estimated_cash_needed) {
        const legCash = (res.data.legs || []).map((leg: Record<string, unknown>, i: number) => ({
          leg: i + 1,
          origin: (leg.origin as string) || release.route_legs[i]?.origin || '',
          destination: (leg.destination as string) || release.route_legs[i]?.destination || '',
          landing_fee_usd: (leg as Record<string, number>).landing_fee_usd || 0,
          overnight_parking_usd: (leg as Record<string, number>).overnight_parking_usd || 0,
          handling_fee_usd: (leg as Record<string, number>).handling_fee_usd || 0,
          customs_fee_usd: (leg as Record<string, number>).customs_fee_usd || 0,
          overflight_permit_cost_usd: (leg as Record<string, number>).overflight_permit_cost_usd || 0,
          payment_type: 'mixed' as const,
          estimated_cash_needed: (leg.estimated_cash_needed as number) || 0,
        }))
        setLandingCostLegs(legCash)
      }
    } catch {
      // API not available — keep mock data
    }
    setRefreshingCosts(false)
  }

  const handleSignPreflight = () => {
    setPreflightSaved(true)
  }

  const handlePrint = () => {
    window.print()
  }

  const handleFetchWeather = async () => {
    setFetchingWeather(true)
    try {
      await api.post(`/api/v1/flight-releases/${release.id}/fetch-weather`)
    } catch {
      // API not available — silently handle
    }
    setFetchingWeather(false)
  }

  return (
    <>
      <style dangerouslySetInnerHTML={{
        __html: `
.print-only { display: none; }
@media print {
  body > *:not(#release-print-content) { display: none !important; }
  #release-print-content { display: block !important; position: absolute; left: 0; top: 0; width: 100%; padding: 0.5in; }
  #release-print-content,
  #release-print-content * { color: #000 !important; background: #fff !important; }
  #release-print-content .border-border\\/50,
  #release-print-content .border-border\\/30,
  #release-print-content .border-border\\/20 { border-color: #ccc !important; }
  #release-print-content .text-muted-foreground { color: #555 !important; }
  #release-print-content .bg-muted\\/30,
  #release-print-content .bg-muted\\/20,
  #release-print-content .bg-muted { background: #f5f5f5 !important; }
  #release-print-content .no-print { display: none !important; }
  #release-print-content button { display: none !important; }
  #release-print-content .text-green-500 { color: #006400 !important; }
  #release-print-content .text-amber-500 { color: #996515 !important; }
  #release-print-content .text-red-500 { color: #8b0000 !important; }
  #release-print-content .text-blue-500 { color: #00008b !important; }
  #release-print-content th { border-bottom: 1px solid #000 !important; }
  #release-print-content table { border-collapse: collapse; width: 100%; }
  #release-print-content td { border-bottom: 1px solid #ddd !important; }
  @page { margin: 0.75in; }

  /* ── Print-only content ── */
  .screen-only { display: none !important; }
  .print-only { display: block !important; }

  /* ── Print Release Document ── */
  .print-release-document { max-width: 100%; }
  .print-release-document * { color: #000 !important; background: #fff !important; }

  /* Header */
  .print-header-bar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
  .print-header-org { font-size: 10pt; font-weight: 700; letter-spacing: 2pt; color: #333 !important; margin: 0 0 4px; }
  .print-header-title { font-size: 18pt; font-weight: 900; margin: 0 0 4px; }
  .print-header-subtitle { font-size: 11pt; color: #555 !important; margin: 0; }
  .print-status-badge { display: inline-block; padding: 4px 12px; border: 1px solid #000; border-radius: 4px; font-size: 9pt; font-weight: 700; }

  /* Summary bar */
  .print-summary-bar { display: flex; flex-wrap: wrap; gap: 6px; font-size: 9pt; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 16px; }
  .print-summary-bar span { color: #333 !important; }

  /* Section headers */
  .print-section-header { margin-top: 18px; margin-bottom: 8px; }
  .print-section-title { font-size: 12pt; font-weight: 800; margin: 0 0 2px; }
  .print-section-rule { border: none; border-top: 2px solid #000; margin: 0; }

  /* Field rows */
  .print-field-row { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dotted #ddd; font-size: 9pt; }
  .print-field-label { color: #555 !important; }
  .print-field-value { font-weight: 600; }

  /* Grid */
  .print-grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
  .print-metar-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 10px; }

  /* Tables */
  .print-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
  .print-table th { text-align: left; padding: 4px 6px; border-bottom: 1px solid #000 !important; font-weight: 700; font-size: 8pt; }
  .print-table td { padding: 3px 6px; border-bottom: 1px solid #ddd !important; }
  .print-table tbody tr:nth-child(even) { background: #f9f9f9 !important; }
  .print-mono { font-family: 'Courier New', Courier, monospace; font-size: 8pt; }
  .print-bold { font-weight: 700; }
  .print-muted { color: #666 !important; }
  .print-total-row { border-top: 2px solid #000 !important; font-weight: 700; }
  .print-total-label { text-align: right; padding-right: 8px; }

  /* Note boxes */
  .print-note-box { padding: 8px 10px; border: 1px solid #ddd; border-radius: 3px; margin-top: 6px; font-size: 9pt; }
  .print-note-label { font-weight: 700; font-size: 8.5pt; margin: 0 0 2px; color: #444 !important; }
  .print-overview-text { margin: 2px 0 0; font-size: 9pt; }

  /* Weather (METAR/TAF) */
  .print-metar-block { border: 1px solid #ccc; border-radius: 3px; padding: 6px 8px; }
  .print-metar-label { font-weight: 700; font-size: 8.5pt; margin: 0 0 4px; }
  .print-raw-weather { margin-top: 2px; }
  .print-raw-label { font-size: 7.5pt; font-weight: 600; color: #555 !important; margin: 0 0 1px; }
  .print-raw-text { font-family: 'Courier New', Courier, monospace; font-size: 7.5pt; margin: 0; white-space: pre-wrap; word-break: break-all; background: #f5f5f5 !important; padding: 4px 6px; border-radius: 2px; }
  .print-raw-missing { font-size: 8pt; font-style: italic; color: #888 !important; margin: 0; }

  /* NOTAMs */
  .print-notam-list { display: flex; flex-direction: column; gap: 6px; }
  .print-notam-item { padding: 6px 8px; border: 1px solid #ddd; border-radius: 3px; font-size: 8.5pt; }
  .print-notam-header { display: flex; gap: 8px; align-items: center; margin-bottom: 2px; }
  .print-notam-code { font-family: 'Courier New', Courier, monospace; font-size: 8pt; font-weight: 600; }
  .print-notam-severity { font-size: 7.5pt; padding: 1px 6px; border: 1px solid #ccc; border-radius: 2px; text-transform: lowercase; }
  .print-notam-info { color: #006 !important; border-color: #88f !important; }
  .print-notam-caution { color: #960 !important; border-color: #fc0 !important; }
  .print-notam-warning { color: #800 !important; border-color: #f44 !important; font-weight: 700; }
  .print-notam-airport { font-size: 8pt; color: #555 !important; }
  .print-notam-desc { margin: 2px 0; }
  .print-notam-dates { font-size: 7.5pt; color: #666 !important; }

  /* Fuel balance */
  .print-fuel-balance { display: flex; justify-content: space-between; padding: 8px 10px; border: 1px solid #ccc; border-radius: 3px; margin-top: 6px; font-size: 9pt; font-weight: 700; }
  .print-balance-ok { color: #060 !important; }
  .print-balance-fail { color: #800 !important; }

  /* Mitigation */
  .print-mitigation { margin-top: 6px; }
  .print-mitigation-list { margin: 4px 0 0; padding-left: 20px; font-size: 9pt; }
  .print-mitigation-list li { margin-bottom: 2px; }

  /* Maintenance */
  .print-mx-safe { padding: 8px 10px; border: 2px solid #060; border-radius: 3px; margin-top: 6px; }
  .print-safe-label { font-weight: 900; font-size: 10pt; color: #060 !important; margin: 0 0 4px; }

  /* Gripes */
  .print-gripe-list { display: flex; flex-direction: column; gap: 6px; }
  .print-gripe-item { padding: 6px 8px; border: 1px solid #ddd; border-radius: 3px; font-size: 8.5pt; }
  .print-gripe-header { display: flex; gap: 8px; align-items: center; margin-bottom: 2px; }
  .print-gripe-desc { font-weight: 600; }
  .print-gripe-badge { font-size: 7.5pt; padding: 1px 6px; border: 1px solid #ccc; border-radius: 2px; text-transform: lowercase; }
  .print-gripe-meta { font-size: 8pt; color: #555 !important; margin: 1px 0; }
  .print-gripe-mx { font-size: 8pt; color: #555 !important; margin: 2px 0 0; font-style: italic; }

  /* Empty state */
  .print-empty-text { font-size: 9pt; font-style: italic; color: #666 !important; }

  /* Signature blocks */
  .print-signature-section { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 14px; margin-bottom: 14px; }
  .print-signature-block { border: 1px solid #ccc; border-radius: 3px; padding: 10px; }
  .print-sig-label { font-size: 8pt; font-weight: 700; margin: 0 0 8px; text-align: center; }
  .print-sig-line { border-bottom: 1px solid #000; margin-bottom: 6px; height: 24px; }
  .print-sig-meta { font-size: 8pt; color: #555 !important; margin: 0; text-align: center; }

  /* Footer */
  .print-footer { margin-top: 24px; }
  .print-footer-rule { border: none; border-top: 1px solid #000; margin: 0 0 6px; }
  .print-footer-text { display: flex; flex-direction: column; gap: 4px; font-size: 8pt; color: #666 !important; text-align: center; }
  .print-footer-disclaimer { font-size: 7.5pt; font-style: italic; color: #888 !important; }
}
`,
      }} />
      <div id="release-print-content" className="space-y-6">
        {/* Back + Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Button variant="ghost" size="sm" onClick={onBack} className="no-print mb-2 -ml-2 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="mr-1 h-4 w-4" /> Back to Releases
            </Button>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{release.title}</h1>
              <Badge variant="outline" className={cfg.color}>{cfg.label}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {release.flight_number} · {release.aircraft_tail} ({release.aircraft_type}) · Created {fmtDate(release.created_at)}
            </p>
          </div>
          <div className="no-print flex gap-2">
            <Button variant="outline" onClick={handlePrint}>
              <Printer className="mr-1 h-4 w-4" /> Print / PDF
            </Button>
            {isDraft && (
              <Button variant="outline" className="text-blue-500" onClick={onApprove}>
                <PenLine className="mr-1 h-4 w-4" /> Submit
              </Button>
            )}
            {isSubmitted && (
              <>
                <Button variant="outline" className="text-green-500" onClick={onApprove}>
                  <ShieldCheck className="mr-1 h-4 w-4" /> Approve
                </Button>
                <Button variant="outline" className="text-red-500">
                  <AlertTriangle className="mr-1 h-4 w-4" /> Reject
                </Button>
              </>
            )}
            {isDraft && (
              <Button variant="outline" className="text-red-500">
                Cancel Release
              </Button>
            )}
          </div>
        </div>

        {/* Summary Bar */}
        <Card className="border-border/50 bg-muted/30">
          <CardContent className="flex flex-wrap gap-x-8 gap-y-2 p-4 text-sm">
            <div className="flex items-center gap-2">
              <PlaneTakeoff className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{release.departure_airport}</span>
              <ChevronRight className="h-3 w-3 text-muted-foreground" />
              <PlaneLanding className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{release.arrival_airport}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>Dep: {fmtTime(release.scheduled_departure)}</span>
              <span>Arr: {fmtTime(release.scheduled_arrival)}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span>Alt: {release.alternate_airport}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">PIC:</span>
              <span className="font-medium">{release.pilot_in_command}</span>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="flight-identity" className="w-full no-print">
          <TabsList className="no-print flex flex-wrap h-auto gap-1">
            <TabsTrigger value="flight-identity" className="text-xs">Flight Identity</TabsTrigger>
            <TabsTrigger value="crew-duty" className="text-xs">Crew & Duty</TabsTrigger>
            <TabsTrigger value="route-navlog" className="text-xs">Route / Nav Log</TabsTrigger>
            <TabsTrigger value="weather" className="text-xs">Weather</TabsTrigger>
            <TabsTrigger value="notams" className="text-xs">NOTAMs</TabsTrigger>
            <TabsTrigger value="fuel" className="text-xs">Fuel Plan</TabsTrigger>
            <TabsTrigger value="hot-zone" className="text-xs">Hot-Zone</TabsTrigger>
            <TabsTrigger value="maintenance" className="text-xs">Maintenance</TabsTrigger>
            <TabsTrigger value="gripes" className="text-xs">Gripes</TabsTrigger>
            <TabsTrigger value="authorizations" className="text-xs">Authorizations</TabsTrigger>
          </TabsList>

        {/* Flight Identity */}
        <TabsContent value="flight-identity" className="mt-4">
          <SectionCard title="Flight Identity" icon={<FileText className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-0">
                <FieldRow label="Flight Number" value={release.flight_number} />
                <FieldRow label="Mission Name" value={release.mission_name} />
                <FieldRow label="Departure Airport" value={release.departure_airport} />
                <FieldRow label="Arrival Airport" value={release.arrival_airport} />
                <FieldRow label="Alternate Airport" value={release.alternate_airport} />
              </div>
              <div className="space-y-0">
                <FieldRow label="Aircraft Tail" value={release.aircraft_tail} />
                <FieldRow label="Aircraft Type" value={release.aircraft_type} />
                <FieldRow label="Scheduled Departure" value={fmtDate(release.scheduled_departure)} />
                <FieldRow label="Scheduled Arrival" value={fmtDate(release.scheduled_arrival)} />
              </div>
            </div>
          </SectionCard>
        </TabsContent>

        {/* Crew & Duty */}
        <TabsContent value="crew-duty" className="mt-4">
          <SectionCard title="Crew & Duty" icon={<UserCheck className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-0">
                <FieldRow label="Pilot in Command" value={release.pilot_in_command} />
                <FieldRow label="Second in Command" value={release.second_in_command} />
              </div>
              <div className="space-y-0">
                <FieldRow label="Crew Duty Time" value={release.crew_duty_time} />
                <FieldRow label="Crew Rest Period" value={release.crew_rest_period} />
              </div>
            </div>
            {release.crew_notes && (
              <div className="mt-3 rounded-md border border-border/30 bg-muted/20 p-3 text-sm">
                <span className="text-muted-foreground">Notes: </span>
                {release.crew_notes}
              </div>
            )}
          </SectionCard>
        </TabsContent>

        {/* Route / Nav Log */}
        <TabsContent value="route-navlog" className="mt-4">
          <SectionCard title="Route / Nav Log" icon={<MapPin className="h-4 w-4" />}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Leg</th>
                    <th className="py-2 pr-3 font-medium">Origin</th>
                    <th className="py-2 pr-3 font-medium">Dest</th>
                    <th className="py-2 pr-3 font-medium">Alt</th>
                    <th className="py-2 pr-3 font-medium">Dist (nm)</th>
                    <th className="py-2 pr-3 font-medium">Alt</th>
                    <th className="py-2 pr-3 font-medium">Wind</th>
                    <th className="py-2 pr-3 font-medium">ETE</th>
                    <th className="py-2 font-medium">Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {release.route_legs.map((leg) => (
                    <tr key={leg.leg} className="border-b border-border/20">
                      <td className="py-2 pr-3 font-mono text-xs">{leg.leg}</td>
                      <td className="py-2 pr-3 font-medium">{leg.origin}</td>
                      <td className="py-2 pr-3 font-medium">{leg.destination}</td>
                      <td className="py-2 pr-3">{leg.alt}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{leg.distance_nm}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{leg.altitude}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{leg.wind}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{leg.time_enroute}</td>
                      <td className="py-2 text-muted-foreground">{leg.remarks}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border/50 font-medium">
                    <td colSpan={4} className="py-2 pr-3 text-right">Totals:</td>
                    <td className="py-2 pr-3 font-mono text-xs">
                      {release.route_legs.reduce((s, l) => s + l.distance_nm, 0)}
                    </td>
                    <td colSpan={3} className="py-2 pr-3 font-mono text-xs">
                      {release.route_legs.reduce((s, l) => {
                        const [m, sec] = l.time_enroute.split(':').map(Number)
                        return s + m + sec / 60
                      }, 0).toFixed(1)} hrs
                    </td>
                    <td className="py-2" />
                  </tr>
                </tfoot>
              </table>
            </div>
          </SectionCard>
        </TabsContent>

        {/* Weather Brief */}
        <TabsContent value="weather" className="mt-4">
          <SectionCard title="Weather Brief" icon={<CloudSun className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldRow label="Source" value={release.weather_source} />
              <FieldRow label="Briefed At" value={fmtDate(release.weather_brief_time)} />
            </div>
            <div className="mt-3 rounded-md border border-border/30 bg-muted/20 p-3">
              <p className="text-sm text-muted-foreground">Weather Overview</p>
              <p className="mt-1 text-sm">{release.weather_overview}</p>
            </div>

            {/* METAR / TAF Cards */}
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <MetarCard
                label={`Departure (${release.departure_airport}) — METAR`}
                metar={release.weather_brief.departure_metar}
                taf={release.weather_brief.departure_taf}
              />
              <MetarCard
                label={`Destination (${release.arrival_airport}) — METAR`}
                metar={release.weather_brief.destination_metar}
                taf={release.weather_brief.destination_taf}
              />
              <MetarCard
                label={`Alternate (${release.alternate_airport}) — METAR`}
                metar={release.weather_brief.alternate_metar}
                taf={release.weather_brief.alternate_taf}
              />
            </div>

            {/* Fetch Live Weather button */}
            {!release.weather_brief.departure_metar &&
              !release.weather_brief.destination_metar &&
              !release.weather_brief.alternate_metar && (
                <div className="no-print mt-4 flex justify-center">
                  <Button variant="outline" onClick={handleFetchWeather} disabled={fetchingWeather}>
                    {fetchingWeather ? (
                      <>Fetching Weather…</>
                    ) : (
                      <><CloudSun className="mr-2 h-4 w-4" /> Fetch Live Weather</>
                    )}
                  </Button>
                </div>
              )}
          </SectionCard>
        </TabsContent>

        {/* NOTAMs */}
        <TabsContent value="notams" className="mt-4">
          <SectionCard title="NOTAMs" icon={<AlertTriangle className="h-4 w-4" />}>
            <div className="space-y-3">
              {release.notams.map((notam) => {
                const severityColors: Record<string, string> = {
                  info: 'border-blue-500/20 bg-blue-500/5',
                  caution: 'border-amber-500/20 bg-amber-500/5',
                  warning: 'border-red-500/20 bg-red-500/5',
                }
                const severityBadgeColors: Record<string, string> = {
                  info: 'bg-blue-500/10 text-blue-500',
                  caution: 'bg-amber-500/10 text-amber-500',
                  warning: 'bg-red-500/10 text-red-500',
                }
                return (
                  <div key={notam.id} className={`rounded-md border p-3 text-sm ${severityColors[notam.severity] || ''}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-medium">{notam.code}</span>
                          <Badge variant="outline" className={severityBadgeColors[notam.severity] || ''}>
                            {notam.severity}
                          </Badge>
                        </div>
                        <p className="mt-1">{notam.description}</p>
                      </div>
                      <span className="whitespace-nowrap text-xs text-muted-foreground">
                        {fmtDate(notam.start_date)} – {fmtDate(notam.end_date)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">Airport: {notam.airport}</p>
                  </div>
                )
              })}
            </div>
          </SectionCard>
        </TabsContent>

        {/* Fuel Plan */}
        <TabsContent value="fuel" className="mt-4">
          <SectionCard title="Fuel Plan" icon={<Fuel className="h-4 w-4" />}>
            <div className="mb-3">
              <FieldRow label="Fuel Type" value={release.fuel_plan.fuel_type} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-0">
                <FieldRow label="Ramp Fuel" value={`${release.fuel_plan.ramp_fuel_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Taxi Fuel" value={`${release.fuel_plan.taxi_fuel_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Trip Fuel" value={`${release.fuel_plan.trip_fuel_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Reserve Fuel" value={`${release.fuel_plan.reserve_fuel_lbs.toLocaleString()} lbs`} />
              </div>
              <div className="space-y-0">
                <FieldRow label="Alternate Fuel" value={`${release.fuel_plan.alternate_fuel_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Final Reserve" value={`${release.fuel_plan.final_reserve_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Total Required" value={`${release.fuel_plan.total_required_lbs.toLocaleString()} lbs`} />
                <FieldRow label="Total Onboard" value={`${release.fuel_plan.total_onboard_lbs.toLocaleString()} lbs`} />
              </div>
            </div>
            <div className="mt-3 rounded-md border border-border/30 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Fuel Balance</span>
                <span className={
                  release.fuel_plan.total_onboard_lbs >= release.fuel_plan.total_required_lbs
                    ? 'text-green-500 font-mono'
                    : 'text-red-500 font-mono'
                }>
                  +{(release.fuel_plan.total_onboard_lbs - release.fuel_plan.total_required_lbs).toLocaleString()} lbs
                  {release.fuel_plan.total_onboard_lbs >= release.fuel_plan.total_required_lbs ? ' ✅' : ' ⚠️'}
                </span>
              </div>
            </div>
          </SectionCard>
        </TabsContent>

        {/* Hot-Zone Assessment */}
        <TabsContent value="hot-zone" className="mt-4">
          <SectionCard title="Hot-Zone Assessment" icon={<AlertTriangle className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldRow label="Threat Level" value={release.hot_zone_assessment.threat_level.toUpperCase()} />
              <FieldRow label="Assessed By" value={release.hot_zone_assessment.assessed_by} />
              <FieldRow label="Assessment Date" value={fmtDate(release.hot_zone_assessment.assessment_date)} />
            </div>
            <div className="mt-3 rounded-md border border-border/30 bg-muted/20 p-3">
              <p className="text-sm text-muted-foreground">Assessment Notes</p>
              <p className="mt-1 text-sm">{release.hot_zone_assessment.notes}</p>
            </div>
            {release.hot_zone_assessment.mitigation_steps.length > 0 && (
              <div className="mt-3">
                <p className="mb-2 text-sm font-medium text-muted-foreground">Mitigation Steps</p>
                <ul className="space-y-1.5">
                  {release.hot_zone_assessment.mitigation_steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-xs font-medium text-amber-500">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </SectionCard>
        </TabsContent>

        {/* Maintenance Control Safe-for-Flight */}
        <TabsContent value="maintenance" className="mt-4">
          <SectionCard title="Maintenance Control — Safe-for-Flight" icon={<Wrench className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldRow label="Maintenance Release" value={release.maintenance_release} />
              <FieldRow label="Engineer" value={release.maintenance_engineer} />
              <FieldRow label="Date Signed" value={fmtDate(release.maintenance_date)} />
            </div>
            {release.maintenance_notes && (
              <div className="mt-3 rounded-md border border-green-500/20 bg-green-500/5 p-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium text-green-500">SAFE FOR FLIGHT</span>
                </div>
                <p className="mt-2 text-sm">{release.maintenance_notes}</p>
              </div>
            )}
          </SectionCard>
        </TabsContent>

        {/* Gripes */}
        <TabsContent value="gripes" className="mt-4">
          <SectionCard title="Gripes (Squawks)" icon={<PenLine className="h-4 w-4" />}>
            {release.gripes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No open gripes.</p>
            ) : (
              <div className="space-y-3">
                {release.gripes.map((gripe) => (
                  <div key={gripe.id} className="rounded-md border border-border/30 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{gripe.description}</span>
                          <GripeBadge severity={gripe.severity} />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Logged: {fmtDate(gripe.date_logged)} · Status: <Badge variant="outline" className={
                            gripe.status === 'resolved' ? 'bg-green-500/10 text-green-500' :
                            gripe.status === 'deferred' ? 'bg-amber-500/10 text-amber-500' :
                            'bg-blue-500/10 text-blue-500'
                          }>{gripe.status}</Badge>
                        </p>
                      </div>
                    </div>
                    {gripe.mechanic_notes && (
                      <div className="mt-2 rounded bg-muted/20 p-2 text-xs text-muted-foreground">
                        <span className="font-medium">MX Notes: </span>{gripe.mechanic_notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </TabsContent>

        {/* Authorizations */}
        <TabsContent value="authorizations" className="mt-4">
          <SectionCard title="Authorizations" icon={<ShieldCheck className="h-4 w-4" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldRow label="Created By" value={release.created_by} />
              <FieldRow label="Authorized By" value={release.authorized_by || '—'} />
              <FieldRow label="Authorization Date" value={release.authorization_date ? fmtDate(release.authorization_date) : '—'} />
            </div>
            {release.release_signature ? (
              <div className="mt-4 rounded-md border border-green-500/20 bg-green-500/5 p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-green-500" />
                  <span className="font-medium text-green-500">Fully Authorized & Released</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  Signed by {release.authorized_by} on {fmtDate(release.authorization_date)}
                </p>
              </div>
            ) : (
              <div className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/5 p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  <span className="font-medium text-amber-500">Pending Authorization</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  This flight release has not yet been authorized for dispatch.
                </p>
              </div>
            )}
          </SectionCard>
        </TabsContent>
      </Tabs>

      {/* ── Weight & Balance Summary ── */}
      <Card className="border-border/50 no-print">
        <CardHeader
          className="flex flex-row items-center justify-between pb-3 cursor-pointer select-none"
          onClick={() => setWbExpanded(!wbExpanded)}
        >
          <CardTitle className="flex items-center gap-2 text-base">
            <Weight className="h-4 w-4 text-brand-400" />
            Weight & Balance Summary
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="no-print h-7 text-xs"
              onClick={(e) => { e.stopPropagation(); handleRefreshWb() }}
              disabled={refreshingWb}
            >
              <RefreshCw className={`mr-1 h-3 w-3 ${refreshingWb ? 'animate-spin' : ''}`} />
              {refreshingWb ? 'Refreshing...' : 'Refresh'}
            </Button>
            {wbExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        {wbExpanded && (
          <CardContent className="pt-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Leg</th>
                    <th className="py-2 pr-3 font-medium">Route</th>
                    <th className="py-2 pr-3 font-medium">Weight (lbs)</th>
                    <th className="py-2 pr-3 font-medium">MTOW (lbs)</th>
                    <th className="py-2 pr-3 font-medium">% MTOW</th>
                    <th className="py-2 pr-3 font-medium">CG</th>
                    <th className="py-2 pr-3 font-medium">T/O Dist</th>
                    <th className="py-2 pr-3 font-medium">Land Dist</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {wbLegs.map((leg) => {
                    const pct = ((leg.total_weight_lbs / leg.mtow_lbs) * 100).toFixed(1)
                    const statusColors: Record<string, string> = {
                      ok: 'text-green-600 bg-green-100 dark:bg-green-900/20 dark:text-green-400',
                      warning: 'text-amber-600 bg-amber-100 dark:bg-amber-900/20 dark:text-amber-400',
                      over_limit: 'text-red-600 bg-red-100 dark:bg-red-900/20 dark:text-red-400',
                    }
                    return (
                      <tr key={leg.leg} className="border-b border-border/20">
                        <td className="py-2 pr-3 font-mono text-xs">{leg.leg}</td>
                        <td className="py-2 pr-3 font-medium">{leg.origin}→{leg.destination}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.total_weight_lbs.toLocaleString()}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.mtow_lbs.toLocaleString()}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{pct}%</td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.cg_position}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.takeoff_distance_ft}ft</td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.landing_distance_ft}ft</td>
                        <td className="py-2">
                          <Badge variant="outline" className={statusColors[leg.status] || ''}>
                            {leg.status === 'ok' ? 'OK' : leg.status === 'warning' ? 'WARNING' : 'OVER LIMIT'}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ── Crew Duty Check ── */}
      <Card className="border-border/50 no-print">
        <CardHeader
          className="flex flex-row items-center justify-between pb-3 cursor-pointer select-none"
          onClick={() => setDutyExpanded(!dutyExpanded)}
        >
          <CardTitle className="flex items-center gap-2 text-base">
            <UserCheck className="h-4 w-4 text-brand-400" />
            Crew Duty Check
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="no-print h-7 text-xs"
              onClick={(e) => { e.stopPropagation(); handleRefreshDuty() }}
              disabled={refreshingDuty}
            >
              <RefreshCw className={`mr-1 h-3 w-3 ${refreshingDuty ? 'animate-spin' : ''}`} />
              {refreshingDuty ? 'Refreshing...' : 'Refresh'}
            </Button>
            {dutyExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        {dutyExpanded && (
          <CardContent className="pt-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Crew Member</th>
                    <th className="py-2 pr-3 font-medium">Role</th>
                    <th className="py-2 pr-3 font-medium">Duty Used</th>
                    <th className="py-2 pr-3 font-medium">Duty Remaining</th>
                    <th className="py-2 pr-3 font-medium">Rest Period</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {crewDutyChecks.map((crew, i) => (
                    <tr key={i} className="border-b border-border/20">
                      <td className="py-2 pr-3 font-medium">{crew.name}</td>
                      <td className="py-2 pr-3">
                        <Badge variant="outline" className={crew.role === 'PIC' ? 'bg-blue-500/10 text-blue-500' : 'bg-purple-500/10 text-purple-500'}>
                          {crew.role}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">{crew.duty_used_hrs.toFixed(1)} hrs</td>
                      <td className="py-2 pr-3 font-mono text-xs">{crew.duty_remaining_hrs.toFixed(1)} hrs</td>
                      <td className="py-2 pr-3 font-mono text-xs">{crew.rest_period_hrs.toFixed(1)} hrs</td>
                      <td className="py-2">
                        <Badge variant="outline" className={crew.pass ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}>
                          {crew.pass ? 'PASS' : 'FAIL'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {crewDutyChecks.some((c) => c.violations.length > 0) && (
                <div className="mt-3 space-y-1">
                  {crewDutyChecks.filter((c) => c.violations.length > 0).map((crew, i) => (
                    <div key={i}>
                      {crew.violations.map((v, j) => (
                        <p key={j} className="text-sm text-red-500 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {crew.name}: {v}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* ── Landing Costs ── */}
      <Card className="border-border/50 no-print">
        <CardHeader
          className="flex flex-row items-center justify-between pb-3 cursor-pointer select-none"
          onClick={() => setCostsExpanded(!costsExpanded)}
        >
          <CardTitle className="flex items-center gap-2 text-base">
            <DollarSign className="h-4 w-4 text-green-400" />
            Landing Costs
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="no-print h-7 text-xs"
              onClick={(e) => { e.stopPropagation(); handleRefreshCosts() }}
              disabled={refreshingCosts}
            >
              <RefreshCw className={`mr-1 h-3 w-3 ${refreshingCosts ? 'animate-spin' : ''}`} />
              {refreshingCosts ? 'Refreshing...' : 'Refresh Costs'}
            </Button>
            {costsExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        {costsExpanded && (
          <CardContent className="pt-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Stop</th>
                    <th className="py-2 pr-3 font-medium">Landing</th>
                    <th className="py-2 pr-3 font-medium">Parking</th>
                    <th className="py-2 pr-3 font-medium">Handling</th>
                    <th className="py-2 pr-3 font-medium">Customs</th>
                    <th className="py-2 pr-3 font-medium">Total</th>
                    <th className="py-2 font-medium">Payment</th>
                  </tr>
                </thead>
                <tbody>
                  {landingCostLegs.map((leg) => {
                    const total = leg.estimated_cash_needed
                    const paymentLabel = leg.payment_type === 'cash_only' ? 'CASH ONLY' : leg.payment_type === 'credit' ? 'Credit OK' : 'Mixed'
                    const paymentClass = leg.payment_type === 'cash_only' ? 'text-red-500 font-bold' : leg.payment_type === 'credit' ? 'text-green-500' : 'text-amber-500'
                    return (
                      <tr key={leg.leg} className="border-b border-border/20">
                        <td className="py-2 pr-3 font-medium">{leg.origin}→{leg.destination}</td>
                        <td className="py-2 pr-3 font-mono text-xs">${leg.landing_fee_usd}</td>
                        <td className="py-2 pr-3 font-mono text-xs">${leg.overnight_parking_usd}</td>
                        <td className="py-2 pr-3 font-mono text-xs">${leg.handling_fee_usd}</td>
                        <td className="py-2 pr-3 font-mono text-xs">${leg.customs_fee_usd}</td>
                        <td className="py-2 pr-3 font-mono text-xs font-medium">${total}</td>
                        <td className={`py-2 text-xs ${paymentClass}`}>{paymentLabel}</td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border/50 font-medium">
                    <td colSpan={5} className="py-2 pr-3 text-right">Estimated Total Cash Needed:</td>
                    <td className="py-2 pr-3 font-mono text-sm font-bold text-green-500">
                      ${landingCostLegs.reduce((s, l) => s + l.estimated_cash_needed, 0)}
                    </td>
                    <td className="py-2" />
                  </tr>
                </tfoot>
              </table>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ── Preflight Checklist ── */}
      <Card className="border-border/50 no-print">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4 text-brand-400" />
            Preflight Checklist — Cost Acknowledgement
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {preflightSaved ? (
            <div className="rounded-md border border-green-500/20 bg-green-500/5 p-4 text-center">
              <ShieldCheck className="mx-auto h-8 w-8 text-green-500" />
              <p className="mt-2 font-medium text-green-500">Preflight Checklist Signed</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Signed by {preflightPic || 'PIC'} on {preflightDate}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md border border-border/30 bg-muted/20 p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Estimated Cash Needed</span>
                  <span className="font-mono text-lg font-bold text-green-500">
                    ${landingCostLegs.reduce((s, l) => s + l.estimated_cash_needed, 0)}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-border accent-green-500"
                    checked={preflightFunds}
                    onChange={(e) => setPreflightFunds(e.target.checked)}
                  />
                  <span className="text-sm">
                    Sufficient funds available for all estimated landing costs
                  </span>
                </label>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-border accent-green-500"
                    checked={preflightPayment}
                    onChange={(e) => setPreflightPayment(e.target.checked)}
                  />
                  <span className="text-sm">
                    Payment type confirmed for each destination
                  </span>
                </label>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">PIC Signature</label>
                <Input
                  placeholder="Type your full name to sign"
                  value={preflightPic}
                  onChange={(e) => setPreflightPic(e.target.value)}
                />
              </div>

              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Date: {preflightDate}</span>
              </div>

              <Button
                className="w-full"
                onClick={handleSignPreflight}
                disabled={!preflightPic.trim() || !preflightFunds || !preflightPayment}
              >
                <ShieldCheck className="mr-2 h-4 w-4" /> Sign Preflight
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Print Release Document ── */}
      <PrintReleaseDocument release={release} />

    </div>
    </>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function DispatchPage() {
  const [releases, setReleases] = useState<FlightRelease[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRelease, setSelectedRelease] = useState<FlightRelease | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  // Create form state — pre-loaded with Caribbean Loop Challenge
  const [formTitle, setFormTitle] = useState('Caribbean Loop Challenge — OP-001')
  const [formFlightNum, setFormFlightNum] = useState('PRC-101')
  const [formMission, setFormMission] = useState('Caribbean Loop Challenge')
  const [formDep, setFormDep] = useState('MYNN')
  const [formArr, setFormArr] = useState('MYNN')
  const [formAlt, setFormAlt] = useState('KMIA')
  const [formAircraftTail, setFormAircraftTail] = useState('N701PR')
  const [formAircraftType, setFormAircraftType] = useState('Cessna Citation CJ4')
  const [formPic, setFormPic] = useState('Capt. Jack D.')
  const [formFo, setFormFo] = useState('FO Sarah K.')
  const [formSchedDep, setFormSchedDep] = useState('2026-07-17T09:00')
  const [formSchedArr, setFormSchedArr] = useState('2026-07-18T01:00')
  const [submitting, setSubmitting] = useState(false)

  const fetchReleases = async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/v1/dispatch/releases')
      // If API returns empty, fall back to mock data
      const data = res.data?.length ? res.data : [DEMO_MISSION]
      setReleases(data)
    } catch {
      // API not available — use mock data
      setReleases([DEMO_MISSION])
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchReleases()
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/v1/dispatch/releases', {
        title: formTitle,
        flight_number: formFlightNum,
        mission_name: formMission,
        departure_airport: formDep,
        arrival_airport: formArr,
        alternate_airport: formAlt,
        aircraft_tail: formAircraftTail,
        aircraft_type: formAircraftType,
        pilot_in_command: formPic,
        second_in_command: formFo,
        scheduled_departure: new Date(formSchedDep).toISOString(),
        scheduled_arrival: new Date(formSchedArr).toISOString(),
      })
      setShowCreate(false)
      resetForm()
      await fetchReleases()
    } catch {
      // API not available — add mock release locally
      const newRelease: FlightRelease = {
        ...DEMO_MISSION,
        id: `rel-${Date.now()}`,
        title: formTitle,
        flight_number: formFlightNum,
        mission_name: formMission,
        departure_airport: formDep,
        arrival_airport: formArr,
        alternate_airport: formAlt,
        aircraft_tail: formAircraftTail,
        aircraft_type: formAircraftType,
        pilot_in_command: formPic,
        second_in_command: formFo,
        scheduled_departure: new Date(formSchedDep).toISOString(),
        scheduled_arrival: new Date(formSchedArr).toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: 'draft',
      }
      setReleases((prev) => [newRelease, ...prev])
      setShowCreate(false)
      resetForm()
    }
    setSubmitting(false)
  }

  const resetForm = () => {
    setFormTitle('Caribbean Loop Challenge — OP-001')
    setFormFlightNum('PRC-101')
    setFormMission('Caribbean Loop Challenge')
    setFormDep('MYNN')
    setFormArr('MYNN')
    setFormAlt('KMIA')
    setFormAircraftTail('N701PR')
    setFormAircraftType('Cessna Citation CJ4')
    setFormPic('Capt. Jack D.')
    setFormFo('FO Sarah K.')
    setFormSchedDep('2026-07-17T09:00')
    setFormSchedArr('2026-07-18T01:00')
  }

  const loadDemoIntoForm = () => {
    setFormTitle('Caribbean Loop Challenge — OP-001')
    setFormFlightNum('PRC-101')
    setFormMission('Caribbean Loop Challenge')
    setFormDep('MYNN')
    setFormArr('MYNN')
    setFormAlt('KMIA')
    setFormAircraftTail('N701PR')
    setFormAircraftType('Cessna Citation CJ4')
    setFormPic('Capt. Jack D.')
    setFormFo('FO Sarah K.')
    setFormSchedDep('2026-07-17T09:00')
    setFormSchedArr('2026-07-18T01:00')
  }

  const handleSubmitRelease = async () => {
    if (!selectedRelease) return
    try {
      await api.patch(`/api/v1/dispatch/releases/${selectedRelease.id}`, {
        status: 'submitted',
      })
      setReleases((prev) =>
        prev.map((r) =>
          r.id === selectedRelease.id ? { ...r, status: 'submitted' as const, updated_at: new Date().toISOString() } : r,
        ),
      )
      setSelectedRelease((prev) =>
        prev ? { ...prev, status: 'submitted' as const, updated_at: new Date().toISOString() } : null,
      )
    } catch {
      // API not available — optimistically update
      setReleases((prev) =>
        prev.map((r) =>
          r.id === selectedRelease.id ? { ...r, status: 'submitted' as const, updated_at: new Date().toISOString() } : r,
        ),
      )
      setSelectedRelease((prev) =>
        prev ? { ...prev, status: 'submitted' as const, updated_at: new Date().toISOString() } : null,
      )
    }
  }

  const handleApproveRelease = async () => {
    if (!selectedRelease) return
    try {
      await api.patch(`/api/v1/dispatch/releases/${selectedRelease.id}`, {
        status: 'approved',
        authorized_by: 'Operations Manager',
        authorization_date: new Date().toISOString(),
        release_signature: 'ops-mgr-sig',
      })
      setReleases((prev) =>
        prev.map((r) =>
          r.id === selectedRelease.id
            ? {
                ...r,
                status: 'approved' as const,
                authorized_by: 'Operations Manager',
                authorization_date: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              }
            : r,
        ),
      )
      setSelectedRelease((prev) =>
        prev
          ? {
              ...prev,
              status: 'approved' as const,
              authorized_by: 'Operations Manager',
              authorization_date: new Date().toISOString(),
              release_signature: 'ops-mgr-sig',
              updated_at: new Date().toISOString(),
            }
          : null,
      )
    } catch {
      // API not available — optimistically update
      setReleases((prev) =>
        prev.map((r) =>
          r.id === selectedRelease.id
            ? {
                ...r,
                status: 'approved' as const,
                authorized_by: 'Operations Manager',
                authorization_date: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              }
            : r,
        ),
      )
      setSelectedRelease((prev) =>
        prev
          ? {
              ...prev,
              status: 'approved' as const,
              authorized_by: 'Operations Manager',
              authorization_date: new Date().toISOString(),
              release_signature: 'ops-mgr-sig',
              updated_at: new Date().toISOString(),
            }
          : null,
      )
    }
  }

  // ── Detail View ──────────────────────────────────────────────────────────
  if (selectedRelease) {
    return (
      <ReleaseDetailView
        release={selectedRelease}
        onBack={() => setSelectedRelease(null)}
        onApprove={selectedRelease.status === 'draft' ? handleSubmitRelease : handleApproveRelease}
      />
    )
  }

  // ── List View ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dispatch</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Flight Release Forms · {releases.length} release{releases.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={() => { loadDemoIntoForm(); setShowCreate(true) }}>
          <Plus className="mr-2 h-4 w-4" /> New Release
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6"><div className="h-20 rounded bg-muted" /></CardContent>
            </Card>
          ))}
        </div>
      ) : releases.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
          <FileSpreadsheet className="h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium text-muted-foreground">No flight releases</p>
          <p className="text-sm text-muted-foreground">Create a new flight release to begin the dispatch process.</p>
          <Button onClick={() => { loadDemoIntoForm(); setShowCreate(true) }}>
            <Plus className="mr-2 h-4 w-4" /> Create Release
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {releases.map((release) => {
            const cfg = STATUS_CONFIG[release.status] || { label: release.status, color: '' }
            return (
              <Card
                key={release.id}
                className="cursor-pointer border-border/50 transition-colors hover:bg-accent/30"
                onClick={() => setSelectedRelease(release)}
              >
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="font-medium truncate">{release.title}</span>
                      <Badge variant="outline" className={cfg.color}>{cfg.label}</Badge>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                      <span className="font-mono text-xs">{release.flight_number}</span>
                      <span>{release.aircraft_tail} ({release.aircraft_type})</span>
                      <span className="flex items-center gap-1">
                        <PlaneTakeoff className="h-3 w-3" />
                        {release.departure_airport}
                      </span>
                      <span>→</span>
                      <span className="flex items-center gap-1">
                        <PlaneLanding className="h-3 w-3" />
                        {release.arrival_airport}
                      </span>
                      <span>PIC: {release.pilot_in_command}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground/70">
                      <span>Created {fmtDate(release.created_at)}</span>
                      <span>{release.route_legs.length} legs</span>
                      <span>{release.route_legs.reduce((s, l) => s + l.distance_nm, 0)} nm total</span>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Create Release Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New Flight Release</DialogTitle>
            <DialogDescription>
              Create a new flight release form. Pre-loaded with Caribbean Loop Challenge demo data.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-3">
              <div className="flex items-center gap-2 text-sm text-blue-500">
                <FileSpreadsheet className="h-4 w-4" />
                <span className="font-medium">Demo Mission: Caribbean Loop Challenge</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                MYNN → KMIA → MMUN → MTPP → MUHA → MDPC → MYNN
              </p>
            </div>

            <h3 className="text-sm font-medium text-muted-foreground">Flight Identity</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Release Title</label>
                <Input value={formTitle} onChange={(e) => setFormTitle(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Flight Number</label>
                <Input value={formFlightNum} onChange={(e) => setFormFlightNum(e.target.value.toUpperCase())} required />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Mission Name</label>
              <Input value={formMission} onChange={(e) => setFormMission(e.target.value)} required />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Departure (ICAO)</label>
                <Input value={formDep} onChange={(e) => setFormDep(e.target.value.toUpperCase())} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Arrival (ICAO)</label>
                <Input value={formArr} onChange={(e) => setFormArr(e.target.value.toUpperCase())} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Alternate (ICAO)</label>
                <Input value={formAlt} onChange={(e) => setFormAlt(e.target.value.toUpperCase())} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Aircraft Tail</label>
                <Input value={formAircraftTail} onChange={(e) => setFormAircraftTail(e.target.value.toUpperCase())} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Aircraft Type</label>
                <Input value={formAircraftType} onChange={(e) => setFormAircraftType(e.target.value)} required />
              </div>
            </div>

            <Separator />

            <h3 className="text-sm font-medium text-muted-foreground">Crew Assignment</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Pilot in Command</label>
                <Input value={formPic} onChange={(e) => setFormPic(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Second in Command</label>
                <Input value={formFo} onChange={(e) => setFormFo(e.target.value)} required />
              </div>
            </div>

            <Separator />

            <h3 className="text-sm font-medium text-muted-foreground">Schedule</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Scheduled Departure</label>
                <Input type="datetime-local" value={formSchedDep} onChange={(e) => setFormSchedDep(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Scheduled Arrival</label>
                <Input type="datetime-local" value={formSchedArr} onChange={(e) => setFormSchedArr(e.target.value)} required />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button type="button" variant="ghost" size="sm" onClick={loadDemoIntoForm} className="text-xs text-muted-foreground">
                Reset to Demo Data
              </Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Creating...' : 'Create Release'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
