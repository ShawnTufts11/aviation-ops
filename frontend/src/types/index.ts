export interface User {
  id: string
  email: string
  display_name: string
  phone: string | null
  role: string
  is_active: boolean
  mfa_enabled: boolean
  feature_overrides?: string[]
  permissions_version?: number
  created_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  logo_url: string | null
  timezone: string
  currency: string
  country: string
  regs: string[]
  is_active: boolean
  created_at: string
}

export interface Aircraft {
  id: string
  tail_number: string
  make: string
  model: string
  year: number
  category: string
  status: string
  base: string
  home_airport: string
  current_cycles: number | null
  current_hours: number | null
  registration_expiry: string | null
  created_at: string
}

export interface Flight {
  id: string
  flight_number: string
  aircraft_id: string
  origin: string
  destination: string
  departure_time: string
  arrival_time: string
  status: string
  pilot_in_command?: string
  passenger_count?: number
  cargo_weight_kg?: number
  notes?: string
  organization_id: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

// ── Weight & Balance ──────────────────────────────────────────────────────
export interface WeightBalance {
  leg_index: number
  origin: string
  destination: string
  passenger_count: number
  crew_count: number
  cargo_kg: number
  fuel_on_board_gal: number
  fuel_burn_gal: number
  weights: {
    basic_empty_kg: number
    crew_kg: number
    passengers_kg: number
    cargo_kg: number
    zero_fuel_kg: number
    fuel_kg: number
    ramp_kg: number
    takeoff_kg: number
    landing_kg: number
  }
  limits: {
    mtow_kg: number
    mlw_kg: number
    max_zfw_kg: number
    max_cargo_kg: number
  }
  margins: {
    mtow_margin_kg: number
    mtow_status: 'ok' | 'warning' | 'over_limit'
    mlw_margin_kg: number
    mlw_status: 'ok' | 'warning' | 'over_limit'
    zfw_margin_kg: number
    zfw_status: 'ok' | 'warning' | 'over_limit'
    cargo_margin_kg: number
    cargo_status: 'ok' | 'warning' | 'over_limit'
  }
  overall_status: 'ok' | 'warning' | 'over_limit'
  notes: string[]
}

// ── Crew Duty ─────────────────────────────────────────────────────────────
export interface CrewMemberDuty {
  name: string
  role: string
  is_pilot: boolean
  rest: {
    last_duty_end: string | null
    rest_hours_received: number
    rest_adequate: boolean
  }
  duty: {
    duty_period_hours: number
    duty_period_exceeded: boolean
    flight_time_hours: number
    flight_time_24hr: number
    flight_time_24hr_exceeded: boolean
    flight_time_quarter_hrs: number
    flight_time_two_quarter_hrs: number
    flight_time_year_hrs: number
  }
  is_legal: boolean
  violations: string[]
  warnings: string[]
}

export interface CrewDuty {
  is_two_pilot: boolean
  flight_time_limit_24hr: number
  departure_time: string
  mission_legal: boolean
  mission_violations: string[]
  crew: CrewMemberDuty[]
}

// ── Route Plan Response ───────────────────────────────────────────────────
export interface RoutePlanLeg {
  leg: number
  origin: string
  destination: string
  distance_nm: number
  block_time_min: number
  block_time_hrs: number
  fuel_gal: number
  weight_balance: WeightBalance | null
  flags: string[]
  is_ok: boolean
}

export interface RoutePlanResponse {
  aircraft: { tail_number: string; type: string }
  legs: RoutePlanLeg[]
  totals: {
    total_distance_nm: number
    total_block_time_min: number
    total_block_hours: number
    total_fuel_gal: number
    total_flight_time_min: number
  }
  crew_duty: CrewDuty | null
  flags: {
    overnight_required: boolean
    crew_swap_required: boolean
    fuel_stop_required: boolean
    critical: string[]
    warnings: string[]
  }
}

// ── Landing Costs ──────────────────────────────────────────────────────────
export type PaymentType = 'cash_only' | 'credit' | 'mixed'

export interface LandingCostLeg {
  leg: number
  origin: string
  destination: string
  landing_fee_usd: number
  overnight_parking_usd: number
  handling_fee_usd: number
  customs_fee_usd: number
  overflight_permit_cost_usd: number
  payment_type: PaymentType
  estimated_cash_needed: number
}

export interface LandingCostsResponse {
  legs: LandingCostLeg[]
  estimated_total_cash_needed: number
}

// ── Cost Reconciliation ────────────────────────────────────────────────────
export interface ActualCosts {
  landing_fee_usd: number
  overnight_parking_usd: number
  handling_fee_usd: number
  customs_fee_usd: number
}

export interface CostReconciliation {
  flight_id: string
  estimated: LandingCostsResponse
  actual: ActualCosts
  variances: {
    landing_fee_variance: number
    overnight_parking_variance: number
    handling_fee_variance: number
    customs_fee_variance: number
    total_variance: number
  }
}

// ── Mission Costs & P&L ────────────────────────────────────────────────────
export type CostCategory = 'fuel' | 'handling' | 'landing' | 'customs' | 'parking' | 'misc'
export type PaymentMethod = 'cash' | 'credit' | 'credit_card' | 'wire'
export type CostCurrency = 'USD' | 'EUR' | 'GBP' | 'HTG' | 'CUP' | 'DOP' | 'MXN'

export interface CostLogEntry {
  id: string
  leg_number: number
  category: CostCategory
  amount: number
  currency: CostCurrency
  payment_method: PaymentMethod
  notes: string | null
  receipt_url: string | null
  logged_by: string
  created_at: string
}

export interface CostLogRequest {
  category: CostCategory
  amount: number
  currency: CostCurrency
  payment_method: PaymentMethod
  notes?: string
  receipt_url?: string
}

export interface PerLegCosts {
  leg_number: number
  departure_airport: string
  arrival_airport: string
  estimated_costs: number
  actual_costs: number
  variance: number
  variance_pct: number
  breakdown: CostLogEntry[]
}

export interface MissionCostsResponse {
  mission_id: string
  legs: PerLegCosts[]
  total_estimated: number
  total_actual: number
  total_variance: number
}

export interface PnlCategoryBreakdown {
  category: CostCategory
  estimated: number
  actual: number
  variance: number
}

export interface MissionPnlResponse {
  mission_id: string
  total_estimated: number
  total_actual: number
  total_variance: number
  status: 'under_budget' | 'on_target' | 'over_budget'
  per_category: PnlCategoryBreakdown[]
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface RegisterResponse {
  access_token: string
  refresh_token: string
  token_type: string
  organization: Organization
  user: User
}
