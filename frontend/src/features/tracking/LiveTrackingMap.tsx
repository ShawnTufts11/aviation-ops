import { useEffect, useRef, useState, useCallback } from 'react'
import { Plane, Crosshair, Layers, Ruler, MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import api from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

interface AircraftPosition {
  tail: string
  lat: number | null
  lon: number | null
  altitude_ft: number | null
  speed_kts: number | null
  heading: number | null
  callsign: string | null
  seen_seconds: number | null
  status?: string
  home_base?: string
}

interface AirportData {
  icao_code: string
  iata_code?: string
  name: string
  city: string
  latitude: number
  longitude: number
  has_jet_a?: boolean
  has_customs?: boolean
  longest_runway_ft?: number
  elevation_ft?: number
  payment_type?: string
}

interface RouteLeg {
  leg_number: number
  departure_icao: string
  arrival_icao: string
  alternate_icao?: string
  departure_lat: number | null
  departure_lon: number | null
  arrival_lat: number | null
  arrival_lon: number | null
  distance_nm: number | null
  status: string
  scheduled_departure?: string
  scheduled_arrival?: string
  flight_time_minutes?: number | null
}

interface MissionRoute {
  mission_id: string
  status: string
  tail: string
  aircraft_id?: string
  home_base?: string
  pilot_in_command?: string
  legs: RouteLeg[]
  polyline: number[][]
  total_legs: number
  total_distance_nm: number
  etp_candidates: { leg: number; departure: string; arrival: string; distance_nm: number; etp_lat: number; etp_lon: number }[]
}

interface NotamMarker {
  icao: string
  lat: number
  lon: number
  id: string
  message: string
  type: string
}

interface LayerToggle {
  id: string
  label: string
  icon: string
  enabled: boolean
  group: 'operational' | 'environmental' | 'overlay'
}

// ── Constants ──────────────────────────────────────────────────────────────

const TAIL_COLORS: Record<string, string> = {
  'N101PB': '#3b82f6',
  'N202PB': '#10b981',
  'N303PB': '#f59e0b',
  'N404PB': '#ef4444',
}

const COLOR_PALETTE = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899',
  '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#e11d48',
]

const ROUTE_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#f472b6']

  // Weather radar tile URLs — RainViewer
  // Uses timestamp-based tiles: https://tilecache.rainviewer.com/v2/radar/{ts}/256/{z}/{x}/{y}/2/1_1.png

function getTailColor(tail: string, index: number): string {
  if (TAIL_COLORS[tail]) return TAIL_COLORS[tail]
  return COLOR_PALETTE[index % COLOR_PALETTE.length]
}

function getRouteColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length]
}

// ── Marker factories ───────────────────────────────────────────────────────

function makePlaneMarker(tail: string, heading: number | null, status?: string, colorIndex?: number): HTMLDivElement {
  const el = document.createElement('div')
  el.className = 'flex items-center justify-center cursor-pointer'
  const color = getTailColor(tail, colorIndex ?? 0)
  const isGrounded = status === 'grounded'
  const opacity = isGrounded ? '44' : '22'
  el.innerHTML = `
    <div style="
      width: ${isGrounded ? 20 : 32}px; height: ${isGrounded ? 20 : 32}px; border-radius: 50%;
      background: ${color}${opacity}; border: ${isGrounded ? 1.5 : 2}px solid ${color};
      display: flex; align-items: center; justify-content: center;
      transform: rotate(${isGrounded ? 0 : heading ?? 0}deg);
      transition: transform 0.3s; opacity: ${isGrounded ? 0.6 : 1};
    ">
      <svg width="${isGrounded ? 10 : 16}" height="${isGrounded ? 10 : 16}" viewBox="0 0 24 24" fill="${color}" stroke="${color}" stroke-width="1">
        <path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
      </svg>
    </div>
  `
  return el
}

function makeAirportMarker(icao: string, hasCustoms?: boolean): HTMLDivElement {
  const el = document.createElement('div')
  el.className = 'flex items-center justify-center cursor-pointer'
  const color = hasCustoms ? '#10b981' : '#64748b'
  el.innerHTML = `
    <div style="
      width: 24px; height: 24px; border-radius: 4px;
      background: ${color}22; border: 2px solid ${color};
      display: flex; align-items: center; justify-content: center;
      font-size: 9px; font-weight: 700; color: ${color};
    ">${icao.slice(0, 2)}</div>
  `
  return el
}

function getFlightCategoryColor(category: string): string {
  switch (category) {
    case 'VFR': return '#22c55e'
    case 'MVFR': return '#3b82f6'
    case 'IFR': return '#f59e0b'
    case 'LIFR': return '#ef4444'
    default: return '#64748b'
  }
}

function makeWeatherMarker(icao: string, category: string): HTMLDivElement {
  const color = getFlightCategoryColor(category)
  const el = document.createElement('div')
  el.className = 'flex items-center justify-center cursor-pointer'
  el.innerHTML = `
    <div style="
      width: 16px; height: 16px; border-radius: 50%;
      background: ${color}; border: 2px solid ${color}88;
      box-shadow: 0 0 6px ${color}44;
    " title="${icao}: ${category}"></div>
  `
  return el
}

function makeNotamMarker(): HTMLDivElement {
  const el = document.createElement('div')
  el.className = 'flex items-center justify-center cursor-pointer'
  el.innerHTML = `<div style="width:14px;height:14px;border-radius:2px;background:#f59e0b33;border:2px solid #f59e0b;display:flex;align-items:center;justify-content:center;font-size:10px;color:#f59e0b;font-weight:700">!</div>`
  return el
}

function makeEtpMarker(): HTMLDivElement {
  const el = document.createElement('div')
  el.innerHTML = `<div style="width:12px;height:12px;transform:rotate(45deg);background:#8b5cf644;border:2px solid #8b5cf6;cursor:pointer" title="Equal Time Point"></div>`
  return el
}

// ── Component ──────────────────────────────────────────────────────────────

export default function LiveTrackingMap() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const airportMarkersRef = useRef<maplibregl.Marker[]>([])
  const weatherMarkersRef = useRef<maplibregl.Marker[]>([])
  const notamMarkersRef = useRef<maplibregl.Marker[]>([])
  const etpMarkersRef = useRef<maplibregl.Marker[]>([])
  const pinMarkersRef = useRef<maplibregl.Marker[]>([])
  const initialFitDone = useRef(false)
  const measurePointsRef = useRef<{lat: number; lon: number}[]>([])
  const measureLineRef = useRef<string[]>([])
  const measureMarkersRef = useRef<maplibregl.Marker[]>([])

  const [positions, setPositions] = useState<AircraftPosition[]>([])
  const [airports, setAirports] = useState<AirportData[]>([])
  const [weather, setWeather] = useState<Record<string, string>>({})
  const [routes, setRoutes] = useState<MissionRoute[]>([])
  const [notams, setNotams] = useState<NotamMarker[]>([])
  const [positionHistory, setPositionHistory] = useState<Record<string, {lat: number; lon: number; heading: number | null; ts: number}[]>>({})
  const [radarTileUrl, setRadarTileUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showLayers, setShowLayers] = useState(false)
  const [tailToggles, setTailToggles] = useState<Record<string, boolean>>({})
  const [mapReady, setMapReady] = useState(false)
  const [activeTool, setActiveTool] = useState<'none' | 'measure' | 'pin'>('none')
  const [layers, setLayers] = useState<LayerToggle[]>([
    { id: 'fleet', label: 'Our Fleet', icon: 'plane', enabled: true, group: 'operational' },
    { id: 'routes', label: 'Active Routes', icon: 'route', enabled: true, group: 'operational' },
    { id: 'progress', label: 'Progress Tracker', icon: 'target', enabled: true, group: 'operational' },
    { id: 'fuel', label: 'Fuel Range Rings', icon: 'circle', enabled: false, group: 'operational' },
    { id: 'etp', label: 'ETP Markers', icon: 'diamond', enabled: false, group: 'operational' },
    { id: 'trail', label: 'Position Trail', icon: 'trail', enabled: true, group: 'operational' },
    { id: 'airports', label: 'Airports', icon: 'airport', enabled: true, group: 'environmental' },
    { id: 'weather', label: 'Weather (METAR)', icon: 'cloud', enabled: false, group: 'environmental' },
    { id: 'radar', label: 'Weather Radar', icon: 'radar', enabled: false, group: 'environmental' },
    { id: 'notams', label: 'NOTAMs', icon: 'alert', enabled: false, group: 'overlay' },
  ])

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const toggleLayer = (id: string) => {
    setLayers(prev => prev.map(l => l.id === id ? { ...l, enabled: !l.enabled } : l))
  }

  // ── Data fetching ────────────────────────────────────────────────────────

  const fetchPositions = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/tracking/live')
      const newPositions: AircraftPosition[] = res.data.aircraft || []
      setPositions(newPositions)
      setError('')

      // Accumulate position history (trail layer)
      setPositionHistory(prev => {
        const next = { ...prev }
        const now = Date.now()
        newPositions.forEach((p: AircraftPosition) => {
          if (p.lat == null || p.lon == null) return
          const trail = next[p.tail] || []
          trail.push({ lat: p.lat, lon: p.lon, heading: p.heading, ts: now })
          // Keep last 120 positions (60 min at 30s intervals)
          if (trail.length > 120) trail.splice(0, trail.length - 120)
          next[p.tail] = trail
        })
        return next
      })
    } catch {
      if (!error) setError('Tracking unavailable')
    }
    setLoading(false)
  }, [])

  const fetchAirports = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/airports?per_page=50')
      setAirports(res.data.airports || res.data.data || [])
    } catch { /* silent */ }
  }, [])

  const fetchWeather = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/ops-checks/weather/briefing')
      const data = res.data?.airports || {}
      setWeather(data)
    } catch { /* silent */ }
  }, [])

  const fetchRoutes = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/tracking/routes')
      setRoutes(res.data.routes || [])
    } catch { /* silent */ }
  }, [])

  const fetchNotams = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/tracking/notams/map')
      setNotams(res.data.notams || [])
    } catch { /* silent */ }
  }, [])

  // Fetch latest RainViewer radar tile URL
  const fetchRadarTile = useCallback(async () => {
    try {
      const res = await fetch('https://api.rainviewer.com/public/weather-maps.json')
      const data = await res.json()
      const past = data?.radar?.past
      if (past && past.length > 0) {
        const latest = past[past.length - 1]
        setRadarTileUrl(`https://tilecache.rainviewer.com${latest.path}/256/{z}/{x}/{y}/2/1_1.png`)
      }
    } catch { /* silent */ }
  }, [])

  // ── Polling ──────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchPositions()
    fetchAirports()
    fetchRoutes()
    fetchRadarTile()

    pollingRef.current = setInterval(() => {
      fetchPositions()
      fetchWeather()
      fetchRoutes()
      fetchNotams()
    }, 30000)

    // Refresh radar tile every 5 min
    const radarPoll = setInterval(fetchRadarTile, 300000)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      clearInterval(radarPoll)
    }
  }, [fetchPositions, fetchAirports, fetchWeather, fetchRoutes, fetchNotams, fetchRadarTile])

  // Sync tail toggles
  useEffect(() => {
    setTailToggles(prev => {
      const next = { ...prev }
      let changed = false
      positions.forEach(p => {
        if (!(p.tail in next)) {
          next[p.tail] = true
          changed = true
        }
      })
      return changed ? next : prev
    })
  }, [positions])

  // ── Map init ─────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!mapContainer.current || map.current) return

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-77.5, 25.0],
      zoom: 6,
      attributionControl: false,
    })

    m.addControl(new maplibregl.NavigationControl(), 'top-left')

    m.on('load', () => {
      map.current = m
      setMapReady(true)
    })

    return () => {
      m.remove()
      map.current = null
    }
  }, [])

  // ── Layer: Fleet markers ────────────────────────────────────────────────

  useEffect(() => {
    if (!map.current) return
    if (!layers.find(l => l.id === 'fleet')?.enabled) {
      markersRef.current.forEach(m => m.remove())
      markersRef.current = []
      return
    }

    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    positions.forEach((p, idx) => {
      if (p.lat == null || p.lon == null) return
      if (tailToggles[p.tail] === false) return

      const el = makePlaneMarker(p.tail, p.heading, p.status, idx)
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([p.lon, p.lat])
        .setPopup(new maplibregl.Popup({ offset: 25, className: 'dark' }).setHTML(`
          <div style="font-family: system-ui; color: #e2e8f0; min-width: 160px;">
            <p style="font-weight: 600; font-size: 14px; margin: 0 0 4px; color: #f1f5f9;">
              ${p.tail}
              ${p.status === 'grounded' ? `<span style="color:#64748b; font-weight:400; font-size:11px;"> (Parked)</span>` : ''}
            </p>
            ${p.callsign ? `<p style="margin: 0; font-size: 12px; color: #94a3b8;">${p.callsign}</p>` : ''}
            ${p.home_base ? `<p style="margin: 2px 0 0; font-size: 11px; color: #64748b;">Home base: ${p.home_base}</p>` : ''}
            <div style="margin-top: 6px; font-size: 12px; color: #94a3b8;">
              ${p.status === 'airborne' && p.speed_kts != null ? `<span>Speed: <strong style="color:#e2e8f0;">${Math.round(p.speed_kts)} kts</strong></span><br>` : ''}
              ${p.status === 'airborne' && p.altitude_ft != null ? `<span>Alt: <strong style="color:#e2e8f0;">${Math.round(p.altitude_ft).toLocaleString()} ft</strong></span><br>` : ''}
              ${p.status === 'airborne' && p.heading != null ? `<span>Heading: <strong style="color:#e2e8f0;">${Math.round(p.heading)}°</strong></span><br>` : ''}
              ${p.status === 'airborne' && p.seen_seconds != null ? `<span style="color:#64748b;">Updated ${p.seen_seconds}s ago</span>` : ''}
              ${p.status === 'grounded' ? '<span style="color:#64748b;">Aircraft on ground</span>' : ''}
            </div>
          </div>
        `))
        .addTo(map.current!)
      markersRef.current.push(marker)
    })

    // Fit bounds only on first data load (don't fight the user zooming)
    if (!initialFitDone.current && positions.length > 0) {
      initialFitDone.current = true
      const bounds = new maplibregl.LngLatBounds()
      positions.forEach(p => {
        if (p.lat != null && p.lon != null) bounds.extend([p.lon, p.lat])
      })
      if (!bounds.isEmpty()) {
        try { map.current.fitBounds(bounds, { padding: 80, maxZoom: 10, duration: 1000 }) } catch {}
      }
    }
  }, [positions, layers, tailToggles])

  // ── Layer: Active Routes (GeoJSON polylines + waypoints) ────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'routes')?.enabled

    // Clean up old route sources/layers
    const routeLayerIds = ['route-lines', 'route-waypoints', 'route-waypoint-labels']
    const routeSourceIds = ['routes-geojson', 'waypoints-geojson']
    routeLayerIds.forEach(id => { try { m.removeLayer(id) } catch {} })
    routeSourceIds.forEach(id => { try { m.removeSource(id) } catch {} })

    if (!enabled || routes.length === 0) return

    // Build GeoJSON feature collection
    const features: any[] = []
    const waypointFeatures: any[] = []

    routes.forEach((r, idx) => {
      const color = getRouteColor(idx)
      // Compute total flight time from legs
      const totalFlightMin = r.legs.reduce((sum, leg) => sum + (leg.flight_time_minutes ?? 0), 0)
      const totalDistance = r.total_distance_nm ?? r.legs.reduce((sum, leg) => sum + (leg.distance_nm ?? 0), 0)
      const hours = Math.floor(totalFlightMin / 60)
      const mins = totalFlightMin % 60
      if (r.polyline.length >= 2) {
        // Build short mission label from ID
        const shortId = r.mission_id?.length > 8 ? r.mission_id.slice(0, 8) : (r.mission_id || '—')
        // Check if PIC is a UUID (looks like a code)
        const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(r.pilot_in_command || '')
        const displayPIC = isUuid ? '—' : (r.pilot_in_command || '—')
        features.push({
          type: 'Feature',
          properties: {
            mission_id: r.mission_id,
            tail: r.tail,
            short_id: shortId,
            status: r.status,
            color,
            total_distance_nm: Math.round(totalDistance * 10) / 10,
            total_legs: r.total_legs ?? r.legs.length,
            total_flight_time: hours > 0 ? `${hours}h ${mins}m` : `${mins}m`,
            pic: displayPIC,
            home_base: r.home_base || '—',
            aircraft_id: r.aircraft_id || r.tail,
          },
          geometry: { type: 'LineString', coordinates: r.polyline },
        })
      }

      // Waypoints
      r.legs.forEach(leg => {
        if (leg.departure_lat != null && leg.departure_lon != null) {
          waypointFeatures.push({
            type: 'Feature',
            properties: {
              icao: leg.departure_icao,
              leg: leg.leg_number,
              type: 'departure',
              color,
              distance_nm: leg.distance_nm,
              status: leg.status,
            },
            geometry: { type: 'Point', coordinates: [leg.departure_lon, leg.departure_lat] },
          })
        }
        if (leg.arrival_lat != null && leg.arrival_lon != null) {
          waypointFeatures.push({
            type: 'Feature',
            properties: {
              icao: leg.arrival_icao,
              leg: leg.leg_number,
              type: 'arrival',
              color,
              distance_nm: leg.distance_nm,
              status: leg.status,
            },
            geometry: { type: 'Point', coordinates: [leg.arrival_lon, leg.arrival_lat] },
          })
        }
      })
    })

    m.addSource('routes-geojson', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features } as any,
    })

    m.addLayer({
      id: 'route-lines',
      type: 'line',
      source: 'routes-geojson',
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 2.5,
        'line-opacity': 0.8,
        'line-dasharray': [1, 0],
      },
    })

    // Waypoints as circles
    m.addSource('waypoints-geojson', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: waypointFeatures } as any,
    })

    m.addLayer({
      id: 'route-waypoints',
      type: 'circle',
      source: 'waypoints-geojson',
      paint: {
        'circle-color': ['get', 'color'],
        'circle-radius': 5,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#0f172a',
      },
    })

    // Waypoint labels
    m.addLayer({
      id: 'route-waypoint-labels',
      type: 'symbol',
      source: 'waypoints-geojson',
      layout: {
        'text-field': ['get', 'icao'],
        'text-offset': [0, -1.5],
        'text-size': 10,
        'text-anchor': 'bottom',
      },
      paint: {
        'text-color': '#94a3b8',
        'text-halo-color': '#0f172a',
        'text-halo-width': 2,
      },
    })

    // Fit bounds to show all routes
    if (routes.length > 0) {
      const allCoords = routes.flatMap(r => r.polyline)
      if (allCoords.length > 0) {
        const bounds = new maplibregl.LngLatBounds()
        allCoords.forEach(c => bounds.extend(c as [number, number]))
        if (!bounds.isEmpty()) {
          m.fitBounds(bounds, { padding: 100, maxZoom: 9, duration: 1000 })
        }
      }
    }

    // ── Route click handler (mission info popup) ──────────────────────────
    const routeClickHandler = (e: any) => {
      const features = m.queryRenderedFeatures(e.point, { layers: ['route-lines'] })
      if (!features || features.length === 0) return
      const p = features[0].properties
      if (!p) return
      const coords = (features[0].geometry as any)?.coordinates
      const center = coords ? coords[Math.floor(coords.length / 2)] : e.lngLat

      // Find full route data for leg breakdown
      const fullRoute = routes.find(r => r.mission_id === p.mission_id)
      let legHtml = ''
      if (fullRoute && fullRoute.legs.length > 0) {
        legHtml = fullRoute.legs.map(leg => {
          const legDist = leg.distance_nm ?? '—'
          const legTime = leg.flight_time_minutes != null
            ? `${Math.floor(leg.flight_time_minutes / 60)}h ${leg.flight_time_minutes % 60}m`
            : '—'
          return `<tr>
            <td style="padding:3px 6px;font-size:12px;color:#64748b;">#${leg.leg_number}</td>
            <td style="padding:3px 6px;font-size:13px;font-weight:600;color:#0f172a;">${leg.departure_icao}</td>
            <td style="padding:3px 6px;font-size:12px;color:#94a3b8;">→</td>
            <td style="padding:3px 6px;font-size:13px;font-weight:600;color:#0f172a;">${leg.arrival_icao}</td>
            <td style="padding:3px 6px;font-size:12px;color:#334155;text-align:right;">${legDist} nm</td>
            <td style="padding:3px 6px;font-size:12px;color:#334155;text-align:right;">${legTime}</td>
          </tr>`
        }).join('')
      }

      new maplibregl.Popup({ offset: 15, closeButton: true, maxWidth: '380px' })
        .setLngLat(center)
        .setHTML(`
          <div style="font-family: system-ui, sans-serif; color: #1e293b; min-width: 280px; font-size: 13px; line-height: 1.4;">
            <!-- Header -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
              <p style="font-weight:700;font-size:15px;margin:0;color:#0f172a;">
                ${p.tail}${p.short_id ? ` · ${p.short_id}` : ''}
              </p>
              <span style="font-size:11px;padding:2px 8px;border-radius:4px;background:${p.color}15;color:${p.color};border:1px solid ${p.color};font-weight:600;">
                ${p.status?.[0]?.toUpperCase() + p.status?.slice(1) || '—'}
              </span>
             </div>
            <!-- Summary row -->
            <div style="display:flex;gap:16px;margin-bottom:8px;font-size:13px;color:#334155;">
              <span>📏 <strong style="color:#0f172a;">${p.total_distance_nm} nm</strong></span>
              <span>⏱ <strong style="color:#0f172a;">${p.total_flight_time}</strong></span>
              <span>🛩 <strong style="color:#0f172a;">${p.total_legs} legs</strong></span>
            </div>
            <!-- Meta row -->
            <div style="font-size:13px;margin-bottom:8px;padding:6px 8px;background:#f1f5f9;border-radius:4px;color:#334155;">
              <span style="font-weight:600;color:#0f172a;">${p.tail}</span>
              ${p.home_base !== '—' ? `<span style="margin-left:12px;">Base: <strong style="color:#0f172a;">${p.home_base}</strong></span>` : ''}
            </div>
            ${legHtml ? `
            <div style="border-top:1px solid #e2e8f0;padding-top:6px;">
              <p style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;margin:0 0 6px;">Legs</p>
              <table style="width:100%;border-collapse:collapse;">
                <thead>
                  <tr style="border-bottom:2px solid #cbd5e1;">
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;text-align:left;font-weight:600;">#</th>
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;text-align:left;font-weight:600;">From</th>
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;"></th>
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;text-align:left;font-weight:600;">To</th>
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;text-align:right;font-weight:600;">Dist</th>
                    <th style="padding:3px 6px;font-size:11px;color:#64748b;text-align:right;font-weight:600;">Time</th>
                  </tr>
                </thead>
                <tbody>${legHtml}</tbody>
              </table>
            </div>` : ''}
          </div>
        `)
        .addTo(m)
    }
    m.on('click', 'route-lines', routeClickHandler)
    // Also change cursor on hover
    m.on('mouseenter', 'route-lines', () => { m.getCanvas().style.cursor = 'pointer' })
    m.on('mouseleave', 'route-lines', () => { m.getCanvas().style.cursor = '' })

    return () => {
      try { m.off('click', 'route-lines', routeClickHandler) } catch {}
    }
  }, [routes, layers, mapReady])

  // ── Layer: Progress Tracker ─────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'progress')?.enabled

    // Clean up old progress markers
    try { m.removeLayer('progress-dots'); m.removeSource('progress-geojson') } catch {}

    if (!enabled || routes.length === 0 || positions.length === 0) return

    // For each airborne aircraft with an active mission, show a progress dot on the route
    const progressFeatures: any[] = []
    positions.forEach(p => {
      if (p.status !== 'airborne' || p.lat == null || p.lon == null) return
      // Find the mission for this aircraft tail
      const route = routes.find(r => r.tail === p.tail)
      if (!route || route.polyline.length < 2) return

      // Find nearest point on route polyline to aircraft position
      let minDist = Infinity
      let nearest: [number, number] | null = null
      for (const coord of route.polyline) {
        const dx = (coord[0] as number) - (p.lon ?? 0)
        const dy = (coord[1] as number) - (p.lat ?? 0)
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < minDist) {
          minDist = dist
          nearest = coord as [number, number]
        }
      }

      if (nearest) {
        progressFeatures.push({
          type: 'Feature',
          properties: {
            tail: p.tail,
            mission_id: route.mission_id,
            heading: p.heading,
            speed_kts: p.speed_kts,
          },
          geometry: { type: 'Point', coordinates: nearest },
        })
      }
    })

    if (progressFeatures.length === 0) return

    m.addSource('progress-geojson', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: progressFeatures } as any,
    })

    m.addLayer({
      id: 'progress-dots',
      type: 'circle',
      source: 'progress-geojson',
      paint: {
        'circle-color': '#f59e0b',
        'circle-radius': 8,
        'circle-opacity': 0.7,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#fbbf24',
      },
    })
  }, [routes, positions, layers, mapReady])

  // ── Layer: ETP Markers ──────────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'etp')?.enabled

    etpMarkersRef.current.forEach(mk => mk.remove())
    etpMarkersRef.current = []

    if (!enabled || routes.length === 0) return

    routes.forEach(r => {
      r.etp_candidates.forEach(etp => {
        const el = makeEtpMarker()
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([etp.etp_lon, etp.etp_lat])
          .setPopup(new maplibregl.Popup({ offset: 15, className: 'dark' }).setHTML(`
            <div style="font-family: system-ui; color: #e2e8f0; min-width: 140px;">
              <p style="font-weight: 600; font-size: 13px; margin: 0; color: #a78bfa;">ETP</p>
              <p style="margin: 2px 0; font-size: 11px; color: #94a3b8;">Leg ${etp.leg}: ${etp.departure} → ${etp.arrival}</p>
              <p style="margin: 0; font-size: 11px; color: #64748b;">${etp.distance_nm} nm</p>
            </div>
          `))
          .addTo(m)
        etpMarkersRef.current.push(marker)
      })
    })
  }, [routes, layers, mapReady])

  // ── Layer: Fuel Range Rings ─────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'fuel')?.enabled

    // Clean up old ring layers
    try { m.removeLayer('fuel-rings-fill'); m.removeLayer('fuel-rings-outline'); m.removeSource('fuel-rings') } catch {}

    if (!enabled || positions.length === 0) return

    // Generate range ring polygons for airborne aircraft
    // 30min ring = ~150nm at 300kts, 1hr = ~300nm, max = fuel endurance
    const ringFeatures: any[] = []
    positions.forEach((p, idx) => {
      if (p.status !== 'airborne' || p.lat == null || p.lon == null) return
      const color = getTailColor(p.tail, idx)

      // Generate circle points at 30min and 1hr range
      // At 300kts: 30min = 150nm, 1hr = 300nm
      // 1 degree ~= 60nm at this latitude
      const ranges = [
        { label: '30min', nm: 150, opacity: 0.08 },
        { label: '1hr', nm: 300, opacity: 0.05 },
      ]

      ranges.forEach(range => {
        const deg = range.nm / 60
        const points: number[][] = []
        for (let angle = 0; angle <= 360; angle += 10) {
          const rad = (angle * Math.PI) / 180
          const dx = deg * Math.cos(rad)
          const dy = deg * Math.sin(rad)
          points.push([p.lon! + dx / Math.cos((p.lat! * Math.PI) / 180), p.lat! + dy])
        }
        ringFeatures.push({
          type: 'Feature',
          properties: { tail: p.tail, label: range.label, color, opacity: range.opacity },
          geometry: { type: 'Polygon', coordinates: [points] },
        })
      })
    })

    if (ringFeatures.length === 0) return

    m.addSource('fuel-rings', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: ringFeatures } as any,
    })

    m.addLayer({
      id: 'fuel-rings-fill',
      type: 'fill',
      source: 'fuel-rings',
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': ['get', 'opacity'],
      },
    })

    m.addLayer({
      id: 'fuel-rings-outline',
      type: 'line',
      source: 'fuel-rings',
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 1,
        'line-opacity': 0.3,
        'line-dasharray': [2, 2],
      },
    })
  }, [positions, layers, mapReady])

  // ── Layer: Weather Radar Tiles ──────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'radar')?.enabled

    try { m.removeLayer('weather-radar'); m.removeSource('weather-radar-tiles') } catch {}

    if (!enabled || !radarTileUrl) return

    m.addSource('weather-radar-tiles', {
      type: 'raster',
      tiles: [radarTileUrl],
      tileSize: 256,
      attribution: 'RainViewer',
      maxzoom: 12,
      minzoom: 4,
    } as any)

    m.addLayer({
      id: 'weather-radar',
      type: 'raster',
      source: 'weather-radar-tiles',
      paint: {
        'raster-opacity': 0.4,
        'raster-resampling': 'linear',
      },
    })
  }, [layers, mapReady, radarTileUrl])

  // ── Layer: Airport markers ──────────────────────────────────────────────

  useEffect(() => {
    if (!map.current) return
    const enabled = layers.find(l => l.id === 'airports')?.enabled

    airportMarkersRef.current.forEach(m => m.remove())
    airportMarkersRef.current = []

    if (!enabled || airports.length === 0) return

    airports
      .filter(a => a.latitude && a.longitude)
      .slice(0, 40)
      .forEach(a => {
        const el = makeAirportMarker(a.icao_code, a.has_customs)
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([a.longitude, a.latitude])
          .setPopup(new maplibregl.Popup({ offset: 15, className: 'dark' }).setHTML(`
            <div style="font-family: system-ui; color: #e2e8f0; min-width: 180px;">
              <p style="font-weight: 600; font-size: 13px; margin: 0; color: #f1f5f9;">${a.icao_code} · ${a.iata_code || ''}</p>
              <p style="margin: 2px 0 0; font-size: 11px; color: #94a3b8;">${a.name || a.city || ''}</p>
              <div style="margin-top: 6px; font-size: 11px; color: #94a3b8;">
                ${a.longest_runway_ft ? `<span>Runway: <strong style="color:#e2e8f0;">${a.longest_runway_ft}'</strong></span><br>` : ''}
                ${a.elevation_ft != null ? `<span>Elevation: <strong style="color:#e2e8f0;">${a.elevation_ft} ft</strong></span><br>` : ''}
                ${a.has_jet_a ? '<span style="color:#10b981;">Jet-A available</span><br>' : ''}
                ${a.has_customs ? '<span style="color:#10b981;">Customs available</span>' : '<span style="color:#ef4444;">No customs</span>'}
                ${a.payment_type === 'cash_only' ? '<br><span style="color:#f59e0b;">⚠ Cash only</span>' : ''}
              </div>
            </div>
          `))
          .addTo(map.current!)
        airportMarkersRef.current.push(marker)
      })
  }, [airports, layers, mapReady])

  // ── Layer: Weather (METAR) markers ──────────────────────────────────────

  useEffect(() => {
    if (!map.current) return
    const enabled = layers.find(l => l.id === 'weather')?.enabled

    weatherMarkersRef.current.forEach(m => m.remove())
    weatherMarkersRef.current = []

    if (!enabled || Object.keys(weather).length === 0) return

    const entries = Array.isArray(weather)
      ? weather
      : Object.entries(weather).map(([k, v]) => ({
          icao: k,
          category: typeof v === 'string' ? v : (v as any)?.flight_category || 'UNKNOWN',
        }))

    entries.slice(0, 40).forEach((w: any) => {
      const icao = w.icao || w
      const category = w.category || w.flight_category || 'UNKNOWN'
      const airport = airports.find(a => a.icao_code === icao)
      if (!airport) return
      const el = makeWeatherMarker(icao, category)
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([airport.longitude, airport.latitude])
        .setPopup(new maplibregl.Popup({ offset: 15, className: 'dark' }).setHTML(`
          <div style="font-family: system-ui; color: #e2e8f0; min-width: 120px;">
            <p style="font-weight: 600; font-size: 13px; margin: 0; color: #f1f5f9;">${icao}</p>
            <p style="margin: 2px 0 0; font-size: 11px; color: ${getFlightCategoryColor(category)};">${category}</p>
          </div>
        `))
        .addTo(map.current!)
      weatherMarkersRef.current.push(marker)
    })
  }, [weather, airports, layers, mapReady])

  // ── Layer: NOTAM markers ────────────────────────────────────────────────

  useEffect(() => {
    if (!map.current) return
    const enabled = layers.find(l => l.id === 'notams')?.enabled

    notamMarkersRef.current.forEach(m => m.remove())
    notamMarkersRef.current = []

    if (!enabled || notams.length === 0) return

    notams.forEach(n => {
      const el = makeNotamMarker()
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([n.lon, n.lat])
        .setPopup(new maplibregl.Popup({ offset: 15, className: 'dark' }).setHTML(`
          <div style="font-family: system-ui; color: #e2e8f0; min-width: 200px;">
            <p style="font-weight: 600; font-size: 13px; margin: 0; color: #f59e0b;">NOTAM · ${n.icao}</p>
            <p style="margin: 4px 0 0; font-size: 11px; color: #94a3b8;">${n.message || 'No details'}</p>
            ${n.type ? `<p style="margin: 2px 0 0; font-size: 10px; color: #64748b;">Type: ${n.type}</p>` : ''}
          </div>
        `))
        .addTo(map.current!)
      notamMarkersRef.current.push(marker)
    })
  }, [notams, layers, mapReady])

  // ── Layer: Position Trail ───────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m) return
    const enabled = layers.find(l => l.id === 'trail')?.enabled

    // Clean up
    const trailLayerIds: string[] = []
    const trailSourceIds: string[] = []
    Object.keys(positionHistory).forEach(tail => {
      trailLayerIds.push(`trail-${tail}`, `trail-${tail}-glow`)
      trailSourceIds.push(`trail-src-${tail}`)
    })
    trailLayerIds.forEach(id => { try { m.removeLayer(id) } catch {} })
    trailSourceIds.forEach(id => { try { m.removeSource(id) } catch {} })

    if (!enabled) return

    // Draw a fading trail for each aircraft
    Object.entries(positionHistory).forEach(([tail, trail]) => {
      if (trail.length < 2) return

      const color = getTailColor(tail, Object.keys(positionHistory).indexOf(tail))
      const coords = trail.map(p => [p.lon, p.lat])

      try {
        m.addSource(`trail-src-${tail}`, {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: { type: 'LineString', coordinates: coords },
          } as any,
        })

        // Glow layer
        m.addLayer({
          id: `trail-${tail}-glow`,
          type: 'line',
          source: `trail-src-${tail}`,
          paint: {
            'line-color': color,
            'line-width': 6,
            'line-opacity': 0.15,
          },
        })

        // Main trail line
        m.addLayer({
          id: `trail-${tail}`,
          type: 'line',
          source: `trail-src-${tail}`,
          paint: {
            'line-color': color,
            'line-width': 2,
            'line-opacity': 0.5,
            'line-dasharray': [3, 2],
          },
        })
      } catch { /* source may already exist from previous render, skip */ }
    })
  }, [positionHistory, layers, mapReady])

  // ── Tool: Measure Distance ─────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m || activeTool !== 'measure') return

    const clickHandler = (e: any) => {
      const pt = e.lngLat
      measurePointsRef.current.push({ lat: pt.lat, lon: pt.lng })

      if (measurePointsRef.current.length === 1) {
        // First click — drop a starting marker
        const el = document.createElement('div')
        el.innerHTML = '<div style="width:12px;height:12px;border-radius:50%;background:#22c55e;border:2px solid #fff;box-shadow:0 0 4px #0006;cursor:pointer;" title="Start"></div>'
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([pt.lng, pt.lat])
          .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML('<div style="color:#0f172a;font-size:12px;font-family:system-ui,sans-serif;font-weight:600;">Start</div>'))
          .addTo(m)
        measureMarkersRef.current.push(marker)
      } else if (measurePointsRef.current.length === 2) {
        // Second click — draw line + show distance
        const [p1, p2] = measurePointsRef.current
        const R = 3440.065 // Earth radius in NM
        const dLat = (p2.lat - p1.lat) * Math.PI / 180
        const dLon = (p2.lon - p1.lon) * Math.PI / 180
        const a = Math.sin(dLat/2)**2 + Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) * Math.sin(dLon/2)**2
        const distanceNM = Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)))

        // Draw line
        const linePoints = [[p1.lon, p1.lat], [p2.lon, p2.lat]]
        const lineSourceId = `measure-line-${Date.now()}`
        try {
          m.addSource(lineSourceId, {
            type: 'geojson',
            data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: linePoints } },
          } as any)
          m.addLayer({
            id: lineSourceId,
            type: 'line',
            source: lineSourceId,
            paint: { 'line-color': '#22c55e', 'line-width': 2, 'line-opacity': 0.8, 'line-dasharray': [4, 2] },
          })
          measureLineRef.current.push(lineSourceId)
        } catch {}

        // Drop end marker with distance
        const el = document.createElement('div')
        el.innerHTML = `<div style="width:12px;height:12px;border-radius:50%;background:#ef4444;border:2px solid #fff;box-shadow:0 0 4px #0006;cursor:pointer;" title="End"></div>`
        const endMarker = new maplibregl.Marker({ element: el })
          .setLngLat([p2.lon, p2.lat])
          .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML(`<div style="color:#0f172a;font-size:14px;font-family:system-ui,sans-serif;font-weight:700;">${distanceNM} nm</div>`))
          .addTo(m)
        measureMarkersRef.current.push(endMarker)

        // Reset for next measurement
        measurePointsRef.current = []
      }
    }

    m.on('click', clickHandler)
    m.getCanvas().style.cursor = 'crosshair'
    return () => {
      m.off('click', clickHandler)
      m.getCanvas().style.cursor = ''
    }
  }, [activeTool, mapReady])

  // ── Tool: Drop Pins ────────────────────────────────────────────────────

  useEffect(() => {
    const m = map.current
    if (!m || activeTool !== 'pin') return

    const clickHandler = (e: any) => {
      const pt = e.lngLat

      const el = document.createElement('div')
      el.innerHTML = `<div style="width:20px;height:28px;cursor:pointer;filter:drop-shadow(0 1px 2px #0008);">
        <svg viewBox="0 0 24 36" width="20" height="28">
          <path d="M12 0C7 0 3 4 3 9c0 5 9 25 9 25s9-20 9-25c0-5-4-9-9-9z" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
          <circle cx="12" cy="9" r="4" fill="#fff"/>
        </svg>
      </div>`
      const marker = new maplibregl.Marker({ element: el, anchor: 'bottom' })
        .setLngLat([pt.lng, pt.lat])
        .setPopup(new maplibregl.Popup({ offset: 25, closeButton: true }).setHTML(`
          <div style="font-family:system-ui,sans-serif;color:#334155;min-width:160px;">
            <p style="font-weight:600;font-size:13px;margin:0 0 4px;color:#d97706;">📍 Pin</p>
            <p style="font-size:12px;color:#0f172a;font-weight:600;margin:0;">
              ${pt.lat.toFixed(4)}, ${pt.lng.toFixed(4)}
            </p>
          </div>
        `))
        .addTo(m)
      pinMarkersRef.current.push(marker)
    }

    m.on('click', clickHandler)
    m.getCanvas().style.cursor = 'copy'
    return () => {
      m.off('click', clickHandler)
      m.getCanvas().style.cursor = ''
    }
  }, [activeTool, mapReady])

  // ── Render ──────────────────────────────────────────────────────────────

  const groupedLayers = (group: string) => layers.filter(l => l.group === group)

  const clearOverlays = () => {
    const m = map.current
    // Remove measurement lines
    measureLineRef.current.forEach(id => {
      try { if (m) { m.removeLayer(id); m.removeSource(id) } } catch {}
    })
    measureLineRef.current = []
    // Remove measurement markers
    measureMarkersRef.current.forEach(mk => { try { mk.remove() } catch {} })
    measureMarkersRef.current = []
    // Remove pin markers
    pinMarkersRef.current.forEach(mk => { try { mk.remove() } catch {} })
    pinMarkersRef.current = []
    measurePointsRef.current = []
  }

  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Plane className="h-4 w-4 text-brand-400" />
          Live Flight Tracking
        </CardTitle>
        <div className="flex items-center gap-2">
          {/* Tool buttons */}
          <Button
            variant={activeTool === 'measure' ? 'default' : 'ghost'}
            size="sm"
            className={`h-7 gap-1 text-xs ${activeTool === 'measure' ? 'bg-brand-600 text-white' : ''}`}
            onClick={() => setActiveTool(activeTool === 'measure' ? 'none' : 'measure')}
            title="Measure distance — click two points"
          >
            <Ruler className="h-3.5 w-3.5" />
            {activeTool === 'measure' ? 'Measuring' : 'Measure'}
          </Button>
          <Button
            variant={activeTool === 'pin' ? 'default' : 'ghost'}
            size="sm"
            className={`h-7 gap-1 text-xs ${activeTool === 'pin' ? 'bg-amber-600 text-white' : ''}`}
            onClick={() => setActiveTool(activeTool === 'pin' ? 'none' : 'pin')}
            title="Drop a pin on the map"
          >
            <MapPin className="h-3.5 w-3.5" />
            {activeTool === 'pin' ? 'Pinning' : 'Pin'}
          </Button>
          {(measureLineRef.current.length > 0 || pinMarkersRef.current.length > 0) && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-red-400 hover:text-red-300"
              onClick={clearOverlays}
              title="Clear all measurements and pins"
            >
              Clear
            </Button>
          )}
          <div className="h-4 w-px bg-border/50" />
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={() => setShowLayers(!showLayers)}
            >
              <Layers className="h-3.5 w-3.5" />
              Layers
            </Button>
            {showLayers && (
              <div className="absolute right-0 top-8 z-50 w-56 rounded-lg border border-border bg-popover p-2 shadow-lg max-h-[70vh] overflow-y-auto">
                <p className="mb-1 px-1 text-xs font-medium text-muted-foreground">Operational</p>
                {groupedLayers('operational').map(layer => (
                  <label key={layer.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                    <input type="checkbox" checked={layer.enabled} onChange={() => toggleLayer(layer.id)} className="h-3.5 w-3.5 accent-brand-500" />
                    <span>{layer.label}</span>
                  </label>
                ))}

                {Object.keys(tailToggles).length > 0 && (
                  <>
                    <div className="mt-2 border-t border-border pt-2">
                      <p className="mb-1 px-1 text-xs font-medium text-muted-foreground">Aircraft</p>
                    </div>
                    {Object.entries(tailToggles).map(([tail, enabled]) => (
                      <label key={tail} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted">
                        <input type="checkbox" checked={enabled} onChange={() => setTailToggles(prev => ({ ...prev, [tail]: !prev[tail] }))} className="h-3.5 w-3.5 accent-brand-500" />
                        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: getTailColor(tail, Object.keys(tailToggles).indexOf(tail)) }} />
                        <span>{tail}</span>
                      </label>
                    ))}
                  </>
                )}

                <div className="mt-2 border-t border-border pt-2">
                  <p className="mb-1 px-1 text-xs font-medium text-muted-foreground">Environmental</p>
                  {groupedLayers('environmental').map(layer => (
                    <label key={layer.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                      <input type="checkbox" checked={layer.enabled} onChange={() => toggleLayer(layer.id)} className="h-3.5 w-3.5 accent-brand-500" />
                      <span>{layer.label}</span>
                    </label>
                  ))}
                </div>

                <div className="mt-2 border-t border-border pt-2">
                  <p className="mb-1 px-1 text-xs font-medium text-muted-foreground">Overlay</p>
                  {groupedLayers('overlay').map(layer => (
                    <label key={layer.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                      <input type="checkbox" checked={layer.enabled} onChange={() => toggleLayer(layer.id)} className="h-3.5 w-3.5 accent-brand-500" />
                      <span>{layer.label}</span>
                    </label>
                  ))}
                </div>

                <div className="mt-2 border-t border-border pt-2">
                  <p className="px-1 text-[10px] text-muted-foreground">
                    <span className="inline-block h-2 w-2 rounded-full bg-green-500 mr-1" /> VFR
                    <span className="inline-block h-2 w-2 rounded-full bg-blue-500 ml-2 mr-1" /> MVFR
                    <span className="inline-block h-2 w-2 rounded-full bg-amber-500 ml-2 mr-1" /> IFR
                    <span className="inline-block h-2 w-2 rounded-full bg-red-500 ml-2 mr-1" /> LIFR
                  </p>
                </div>

                {routes.length > 0 && (
                  <div className="mt-2 border-t border-border pt-2">
                    <p className="px-1 text-xs font-medium text-muted-foreground">Active Missions</p>
                    {routes.map((r, i) => (
                      <div key={r.mission_id} className="px-2 py-1 text-xs" style={{ color: getRouteColor(i) }}>
                        <span className="inline-block h-2 w-2 rounded-full mr-1" style={{ backgroundColor: getRouteColor(i) }} />
                        {r.tail} · {r.total_legs} legs · {r.total_distance_nm}nm
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
            {positions.length} aircraft · {routes.length} routes
          </Badge>

          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { fetchPositions(); fetchWeather(); fetchRoutes(); fetchNotams(); }} title="Refresh">
            <Crosshair className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div ref={mapContainer} className="h-[560px] w-full rounded-b-lg" />

        {/* Legend */}

        {/* Footer status bar */}
        <div className="flex flex-wrap gap-3 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span className="font-medium">Fleet:</span>
          {positions
            .filter((p, i, a) => a.findIndex(x => x.tail === p.tail) === i)
            .sort((a, b) => a.tail.localeCompare(b.tail))
            .map((p, i) => (
              <span key={p.tail} className="flex items-center gap-1">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: getTailColor(p.tail, i) }} />
                {p.tail}
              </span>
            ))}
          <span className="text-muted-foreground/50 ml-auto">
            {positions.filter(p => p.status === 'airborne').length} air · {positions.filter(p => p.status === 'grounded').length} ground · {routes.length} active missions · {notams.length} NOTAMs
          </span>
        </div>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/60">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
          </div>
        )}
        {error && (
          <div className="absolute bottom-12 left-4 rounded-md bg-red-500/10 px-3 py-1.5 text-xs text-red-500">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
