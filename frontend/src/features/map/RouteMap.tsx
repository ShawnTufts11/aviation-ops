import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

// ── Types ──────────────────────────────────────────────────────────────────

export interface RouteLeg {
  leg: number
  origin: string
  destination: string
  origin_lat: number
  origin_lon: number
  dest_lat: number
  dest_lon: number
  origin_name?: string
  destination_name?: string
  distance_nm?: number
  destination_intel?: {
    weather?: {
      flight_category?: string  // VFR/MVFR/IFR/LIFR
      temp_f?: number
      wind_speed_kt?: number
      visibility_statute_mi?: number
      raw_metar?: string
    }
    fbo_count?: number
  }
}

interface RouteMapProps {
  legs: RouteLeg[]
  className?: string
}

// ── Flight category colors ─────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, { fill: string; text: string }> = {
  VFR:  { fill: '#22c55e', text: '#052e16' },  // green
  MVFR: { fill: '#3b82f6', text: '#172554' },  // blue
  IFR:  { fill: '#ef4444', text: '#450a0a' },  // red
  LIFR: { fill: '#ec4899', text: '#4c0519' },  // pink/magenta
}

const DEFAULT_COLOR = { fill: '#6b7280', text: '#111827' }

// ── Great circle arc (ported from x-dispatch RouteLineLayer.ts) ─────────

function greatCircleArc(
  from: [number, number],
  to: [number, number],
  numPoints: number = 100
): [number, number][] {
  const [lon1, lat1] = from
  const [lon2, lat2] = to

  const φ1 = (lat1 * Math.PI) / 180
  const λ1 = (lon1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const λ2 = (lon2 * Math.PI) / 180

  const Δσ = Math.acos(
    Math.sin(φ1) * Math.sin(φ2) + Math.cos(φ1) * Math.cos(φ2) * Math.cos(λ2 - λ1)
  )

  if (Δσ < 0.0001) return [from, to]

  const points: [number, number][] = []
  let prevLon: number | null = null
  let lonOffset = 0

  for (let i = 0; i <= numPoints; i++) {
    const f = i / numPoints
    const A = Math.sin((1 - f) * Δσ) / Math.sin(Δσ)
    const B = Math.sin(f * Δσ) / Math.sin(Δσ)

    const x = A * Math.cos(φ1) * Math.cos(λ1) + B * Math.cos(φ2) * Math.cos(λ2)
    const y = A * Math.cos(φ1) * Math.sin(λ1) + B * Math.cos(φ2) * Math.sin(λ2)
    const z = A * Math.sin(φ1) + B * Math.sin(φ2)

    const lat = Math.atan2(z, Math.sqrt(x * x + y * y))
    const lon = Math.atan2(y, x)

    let lonDeg = (lon * 180) / Math.PI
    const latDeg = (lat * 180) / Math.PI

    if (prevLon !== null) {
      const delta = lonDeg - prevLon
      if (delta > 180) lonOffset -= 360
      else if (delta < -180) lonOffset += 360
    }
    prevLon = lonDeg
    lonDeg += lonOffset

    points.push([lonDeg, latDeg])
  }

  return points
}

// ── Airport marker element ────────────────────────────────────────────────

function makeAirportMarker(
  icao: string,
  name: string,
  flightCategory?: string,
  onClick?: () => void
): HTMLDivElement {
  const colors = CATEGORY_COLORS[flightCategory ?? ''] ?? DEFAULT_COLOR
  const el = document.createElement('div')
  el.className = 'cursor-pointer'
  el.title = `${icao} — ${name}`
  el.addEventListener('click', () => onClick?.())

  // Outer ring with category color, inner white circle with ICAO text
  el.innerHTML = `
    <div style="
      display: flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border-radius: 50%;
      background: ${colors.fill}22;
      border: 2px solid ${colors.fill};
      box-shadow: 0 0 8px ${colors.fill}44;
      transition: transform 0.15s;
      font-size: 9px; font-weight: 700; color: ${colors.fill};
    ">
      ${icao}
    </div>
  `
  return el
}

// ── Aircraft marker element ───────────────────────────────────────────────

function makeAircraftMarker(_tail?: string): HTMLDivElement {
  const el = document.createElement('div')
  el.className = 'cursor-pointer'
  el.innerHTML = `
    <div style="
      width: 36px; height: 36px; border-radius: 50%;
      background: #1DA0F222; border: 2.5px solid #1DA0F2;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 10px #1DA0F266;
    ">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="#1DA0F2" stroke="none">
        <path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
      </svg>
    </div>
  `
  return el
}

// ── Weather popup HTML ────────────────────────────────────────────────────

function weatherPopupHtml(
  icao: string,
  name: string,
  wx?: { flight_category?: string; temp_f?: number; wind_speed_kt?: number; visibility_statute_mi?: number; raw_metar?: string }
): string {
  const cat = wx?.flight_category ?? '—'
  return `
    <div style="font-family: system-ui; color: #e2e8f0; min-width: 180px;">
      <p style="font-weight: 600; font-size: 14px; margin: 0 0 2px; color: #f1f5f9;">
        ${icao}
      </p>
      <p style="margin: 0 0 8px; font-size: 11px; color: #94a3b8;">${name}</p>
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
        <span style="
          display: inline-block; padding: 1px 8px; border-radius: 4px;
          font-size: 11px; font-weight: 700;
          background: ${CATEGORY_COLORS[cat]?.fill ?? '#6b7280'}22;
          color: ${CATEGORY_COLORS[cat]?.fill ?? '#6b7280'};
          border: 1px solid ${CATEGORY_COLORS[cat]?.fill ?? '#6b7280'}44;
        ">${cat}</span>
        ${wx?.temp_f != null ? `<span style="font-size: 12px;">${Math.round(wx.temp_f)}°F</span>` : ''}
      </div>
      <div style="font-size: 11px; color: #94a3b8; line-height: 1.6;">
        ${wx?.wind_speed_kt != null ? `<div>Wind: ${wx.wind_speed_kt} kt</div>` : ''}
        ${wx?.visibility_statute_mi != null ? `<div>Vis: ${wx.visibility_statute_mi} mi</div>` : ''}
      </div>
      ${wx?.raw_metar ? `<pre style="margin-top: 6px; font-size: 10px; color: #64748b; white-space: pre-wrap;">${wx.raw_metar}</pre>` : ''}
    </div>
  `
}

// ── Component ─────────────────────────────────────────────────────────────

export default function RouteMap({ legs, className = '' }: RouteMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)

  // Init map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-77.5, 25.0],
      zoom: 5,
      attributionControl: false,
    })

    m.addControl(new maplibregl.NavigationControl(), 'top-left')

    m.on('load', () => {
      mapRef.current = m
      setReady(true)
    })

    return () => {
      m.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [])

  // Draw route lines + markers when ready and legs change
  useEffect(() => {
    if (!ready || !mapRef.current || legs.length === 0) return
    const map = mapRef.current
    const markers: maplibregl.Marker[] = []

    const bounds = new maplibregl.LngLatBounds()

    // ── Collect waypoints ─────────────────────────────────────────────
    const waypoints: { icao: string; name: string; lat: number; lon: number; isOrigin: boolean; wx?: { flight_category?: string; temp_f?: number; wind_speed_kt?: number; visibility_statute_mi?: number; raw_metar?: string } }[] = []

    legs.forEach((leg) => {
      // Add origin (only once)
      if (!waypoints.find(w => w.icao === leg.origin)) {
        waypoints.push({
          icao: leg.origin,
          name: leg.origin_name || leg.origin,
          lat: leg.origin_lat,
          lon: leg.origin_lon,
          isOrigin: true,
        })
      }
      // Add destination
      waypoints.push({
        icao: leg.destination,
        name: leg.destination_name || leg.destination,
        lat: leg.dest_lat,
        lon: leg.dest_lon,
        isOrigin: false,
        wx: leg.destination_intel?.weather,
      })
    })

    // ── Draw route lines ──────────────────────────────────────────────
    const sourceId = 'route-lines'
    const layerId = 'route-line'

    if (map.getSource(sourceId)) {
      ;(map.getSource(sourceId) as maplibregl.GeoJSONSource).setData({
        type: 'FeatureCollection',
        features: [],
      })
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
    }

    if (map.getLayer(layerId)) {
      map.removeLayer(layerId)
    }
    map.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      paint: {
        'line-color': '#1DA0F2',
        'line-width': 3,
        'line-opacity': 0.8,
      },
    })

    // Build route segments
    const features: GeoJSON.Feature[] = []
    for (let i = 0; i < waypoints.length - 1; i++) {
      const from: [number, number] = [waypoints[i].lon, waypoints[i].lat]
      const to: [number, number] = [waypoints[i + 1].lon, waypoints[i + 1].lat]
      const coords = greatCircleArc(from, to, 80)

      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: coords },
        properties: { segment: `${waypoints[i].icao} → ${waypoints[i + 1].icao}` },
      })
    }

    ;(map.getSource(sourceId) as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features,
    })

    // ── Airport markers ───────────────────────────────────────────────
    waypoints.forEach((wp) => {
      const marker = new maplibregl.Marker({
        element: makeAirportMarker(wp.icao, wp.name, wp.wx?.flight_category),
      })
        .setLngLat([wp.lon, wp.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25, className: 'dark' })
            .setHTML(weatherPopupHtml(wp.icao, wp.name, wp.wx))
        )
        .addTo(map)
      markers.push(marker)

      bounds.extend([wp.lon, wp.lat])
    })

    // ── Aircraft marker at first origin ───────────────────────────────
    if (waypoints.length > 0) {
      const first = waypoints[0]
      const acMarker = makeAircraftMarker()
      new maplibregl.Marker({ element: acMarker })
        .setLngLat([first.lon, first.lat])
        .addTo(map)
    }

    // ── Fit bounds ────────────────────────────────────────────────────
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 80, maxZoom: 9, duration: 1000 })
    }

    return () => {
      markers.forEach((m) => m.remove())
      if (map.getLayer) {
        try {
          if (map.getLayer(layerId)) map.removeLayer(layerId)
          if (map.getSource(sourceId)) map.removeSource(sourceId)
        } catch {} // map already destroyed during unmount
      }
    }
  }, [ready, legs])

  return (
    <div className={`relative ${className}`}>
      <div ref={mapContainer} className="h-[400px] w-full rounded-lg border border-border/50" />

      {/* Legend */}
      <div className="flex flex-wrap gap-3 border-t border-border px-4 py-2 text-xs text-muted-foreground">
        <span className="font-medium">Flight Category:</span>
        {(['VFR', 'MVFR', 'IFR', 'LIFR'] as const).map((cat) => (
          <span key={cat} className="flex items-center gap-1">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS[cat].fill }}
            />
            {cat}
          </span>
        ))}
        <span className="ml-auto flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-[#1DA0F2]" />
          Route
        </span>
      </div>
    </div>
  )
}
