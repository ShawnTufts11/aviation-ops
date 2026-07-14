export interface User {
  id: string
  email: string
  display_name: string
  phone: string | null
  role: 'super_admin' | 'ops_manager' | 'admin' | 'pilot' | 'mechanic' | 'readonly'
  is_active: boolean
  mfa_enabled: boolean
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
