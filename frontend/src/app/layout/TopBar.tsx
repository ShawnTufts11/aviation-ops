import { useState, useEffect, useRef, useCallback } from 'react'
import { Bell, Menu, AlertTriangle, LogOut } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { useAuthContext } from '@/features/auth/AuthContext'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'

interface TopBarProps {
  onMenuClick: () => void
}

export default function TopBar({ onMenuClick }: TopBarProps) {
  const { user, logout } = useAuthContext()
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)
  const [notifications, setNotifications] = useState<any[]>([])
  const [showNotifs, setShowNotifs] = useState(false)
  const [now, setNow] = useState(new Date())
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const IDLE_TIMEOUT_MS = 30 * 60 * 1000

  // Idle timer — reset on mouse/keyboard
  const resetIdleTimer = useCallback(() => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
    idleTimerRef.current = setTimeout(() => {
      logout()
      navigate('/login')
    }, IDLE_TIMEOUT_MS)
  }, [logout, navigate])

  useEffect(() => {
    resetIdleTimer()
    const events = ['mousedown', 'keydown', 'mousemove', 'touchstart', 'scroll']
    events.forEach(e => window.addEventListener(e, resetIdleTimer))
    return () => {
      events.forEach(e => window.removeEventListener(e, resetIdleTimer))
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
    }
  }, [resetIdleTimer])

  // Clock tick — updates every second
  useEffect(() => {
    const tick = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(tick)
  }, [])

  const fetchNotifs = async () => {
    try {
      const res = await api.get('/api/v1/comms/notifications?unread_only=true')
      setUnread(res.data.unread_count)
      setNotifications(res.data.data.slice(0, 10))
    } catch { /* silent */ }
  }

  useEffect(() => {
    fetchNotifs()
    pollingRef.current = setInterval(fetchNotifs, 30000)
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
  }, [])

  const markRead = async (id: string) => {
    await api.post(`/api/v1/comms/notifications/${id}/read`)
    fetchNotifs()
  }

  const severityColor = (s: string) => {
    if (s === 'emergency' || s === 'critical') return 'text-red-500'
    if (s === 'warning') return 'text-amber-500'
    return 'text-muted-foreground'
  }

  const initials = user?.display_name
    ? user.display_name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : 'PR'

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background px-4 md:px-6">
      <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex items-center gap-3 text-sm font-medium text-muted-foreground font-mono">
        <span className="flex items-center gap-1">
          <span className="text-xs font-bold text-brand-400">Z</span>
          {now.toLocaleTimeString('en-US', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false })}
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="text-xs font-bold text-amber-400">E</span>
          {now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false })}
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="text-xs font-bold text-green-400">C</span>
          {now.toLocaleTimeString('en-US', { timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit', hour12: false })}
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="text-xs font-bold text-blue-400">L</span>
          {now.toLocaleTimeString('en-US', { timeZone: 'America/Nassau', hour: '2-digit', minute: '2-digit', hour12: true })}
        </span>
      </div>

      <div className="flex-1" />

      {/* Notification Bell */}
      <DropdownMenu open={showNotifs} onOpenChange={setShowNotifs}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            {unread > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-80" align="end" sideOffset={8}>
          <DropdownMenuLabel>
            <div className="flex items-center justify-between">
              <span>Notifications</span>
              {unread > 0 && (
                <button
                  className="text-xs text-brand-400 hover:underline"
                  onClick={async () => { await api.post('/api/v1/comms/notifications/read-all'); fetchNotifs() }}
                >
                  Mark all read
                </button>
              )}
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-center text-sm text-muted-foreground">No new notifications</p>
            ) : (
              notifications.map((n: any) => (
                <DropdownMenuItem
                  key={n.id}
                  className="flex flex-col items-start gap-1 px-4 py-3"
                  onClick={() => markRead(n.id)}
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`h-3.5 w-3.5 shrink-0 ${severityColor(n.severity)}`} />
                    <span className="text-sm font-medium">{n.title}</span>
                  </div>
                  {n.message && <p className="text-xs text-muted-foreground">{n.message}</p>}
                </DropdownMenuItem>
              ))
            )}
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User Avatar Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative flex items-center gap-2 rounded-full">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-brand-600 text-xs text-white">{initials}</AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium md:inline-block">{user?.display_name || 'User'}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-64" align="end" sideOffset={8}>
          <DropdownMenuLabel>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">{user?.display_name || 'User'}</p>
              <p className="text-xs text-muted-foreground">{user?.email || ''}</p>
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                Z {now.toLocaleTimeString('en-US', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false })}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate('/settings')}>Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="flex items-center gap-2 text-destructive focus:text-destructive" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
