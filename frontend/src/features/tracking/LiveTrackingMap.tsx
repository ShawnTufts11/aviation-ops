import { useEffect, useRef, useState, useCallback } from 'react'
import { Plane, Crosshair } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import api from '@/lib/api'

interface AircraftPosition {
  tail: string
  lat: number | null
  lon: number | null
  altitude_ft: number | null
  speed_kts: number | null
  heading: number | null
  callsign: string | null
  seen_seconds: number | null
}

const TAIL_COLORS: Record<string, string> = {
  'C6-BT67': '#3b82f6',  // blue
  'C6-K35X': '#10b981',  // green
  'C6-K200': '#f59e0b',  // amber
  'C6-T300': '#ef4444',  // red
}

function makePlaneMarker(tail: string, heading: number | null): HTMLDivElement {
  const el = document.createElement('div')
  el.className = 'flex items-center justify-center cursor-pointer'
  const color = TAIL_COLORS[tail] || '#8b5cf6'
  el.innerHTML = `
    <div style="
      width: 32px; height: 32px; border-radius: 50%;
      background: ${color}22; border: 2px solid ${color};
      display: flex; align-items: center; justify-content: center;
      transform: rotate(${heading ?? 0}deg);
      transition: transform 0.3s;
    ">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="${color}" stroke="${color}" stroke-width="1">
        <path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
      </svg>
    </div>
  `
  return el
}

export default function LiveTrackingMap() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const [positions, setPositions] = useState<AircraftPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Fetch positions
  const fetchPositions = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/tracking/live')
      setPositions(res.data.aircraft)
      setError('')
    } catch {
      if (!error) setError('Tracking unavailable')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchPositions()
    pollingRef.current = setInterval(fetchPositions, 30000)
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [fetchPositions])

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-77.5, 25.0],  // Bahamas center
      zoom: 6,
      attributionControl: false,
    })

    m.addControl(new maplibregl.NavigationControl(), 'top-left')

    m.on('load', () => {
      map.current = m
    })

    return () => {
      m.remove()
      map.current = null
    }
  }, [])

  // Update markers
  useEffect(() => {
    if (!map.current) return

    // Clear old markers
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []

    // Add markers for each position
    positions.forEach((p) => {
      if (p.lat == null || p.lon == null) return

      const el = makePlaneMarker(p.tail, p.heading)
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([p.lon, p.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25, className: 'dark' }).setHTML(`
            <div style="font-family: system-ui; color: #e2e8f0; min-width: 160px;">
              <p style="font-weight: 600; font-size: 14px; margin: 0 0 4px; color: #f1f5f9;">
                ${p.tail}
              </p>
              ${p.callsign ? `<p style="margin: 0; font-size: 12px; color: #94a3b8;">${p.callsign}</p>` : ''}
              <div style="margin-top: 6px; font-size: 12px; color: #94a3b8;">
                ${p.speed_kts != null ? `<span>Speed: <strong style="color:#e2e8f0;">${Math.round(p.speed_kts)} kts</strong></span><br>` : ''}
                ${p.altitude_ft != null ? `<span>Alt: <strong style="color:#e2e8f0;">${Math.round(p.altitude_ft).toLocaleString()} ft</strong></span><br>` : ''}
                ${p.heading != null ? `<span>Heading: <strong style="color:#e2e8f0;">${Math.round(p.heading)}°</strong></span><br>` : ''}
                ${p.seen_seconds != null ? `<span style="color:#64748b;">Updated ${p.seen_seconds}s ago</span>` : ''}
              </div>
            </div>
          `)
        )
        .addTo(map.current!)
      markersRef.current.push(marker)
    })

    // Fit bounds if any positions exist
    if (positions.length > 0) {
      const bounds = new maplibregl.LngLatBounds()
      positions.forEach((p) => {
        if (p.lat != null && p.lon != null) bounds.extend([p.lon, p.lat])
      })
      if (!bounds.isEmpty()) {
        map.current.fitBounds(bounds, { padding: 80, maxZoom: 10, duration: 1000 })
      }
    }
  }, [positions])

  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Plane className="h-4 w-4 text-brand-400" />
          Live Flight Tracking
        </CardTitle>
        <div className="flex items-center gap-2">
          {positions.length > 0 && (
            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
              {positions.length} aircraft
            </Badge>
          )}
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={fetchPositions} title="Refresh">
            <Crosshair className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div ref={mapContainer} className="h-[400px] w-full rounded-b-lg" />

        {/* Legend */}
        <div className="flex flex-wrap gap-3 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span className="font-medium">Fleet:</span>
          {['C6-BT67', 'C6-K35X', 'C6-K200', 'C6-T300'].map((t) => (
            <span key={t} className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: TAIL_COLORS[t] || '#8b5cf6' }} />
              {t}
            </span>
          ))}
          <span className="ml-auto">Data: ADSB.lol · 30s refresh</span>
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
