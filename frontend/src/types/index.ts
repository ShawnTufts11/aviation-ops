export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'ops_manager' | 'pilot' | 'maintenance' | 'crew' | 'viewer'
  avatar_url?: string
  organization_id: string
  created_at: string
  updated_at: string
}

export interface Organization {
  id: string
  name: string
  icao_code?: string
  iata_code?: string
  callsign?: string
  logo_url?: string
  timezone: string
  created_at: string
  updated_at: string
}

export interface Aircraft {
  id: string
  registration: string
  type: string
  model: string
  year: number
  serial_number: string
  status: 'active' | 'maintenance' | 'grounded' | 'retired'
  cycle_count: number
  airframe_hours: number
  last_inspection: string
  next_inspection: string
  organization_id: string
  created_at: string
  updated_at: string
}

export interface Flight {
  id: string
  flight_number: string
  aircraft_id: string
  origin: string
  destination: string
  departure_time: string
  arrival_time: string
  status: 'scheduled' | 'boarding' | 'departed' | 'en_route' | 'arrived' | 'cancelled' | 'delayed'
  pilot_id: string
  crew_ids: string[]
  passenger_count: number
  cargo_weight_kg?: number
  fuel_gal?: number
  notes?: string
  organization_id: string
  created_at: string
  updated_at: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}
