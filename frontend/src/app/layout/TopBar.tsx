import { useState, useEffect, useRef } from 'react'
import { Bell, Menu, AlertTriangle } from 'lucide-react'
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
import api from '@/lib/api'

interface TopBarProps {
  onMenuClick: () => void
}

export default function TopBar({ onMenuClick }: TopBarProps) {
  const { user, logout } = useAuthContext()
  const [unread, setUnread] = useState(0)
  const [notifications, setNotifications] = useState<any[]>([])
  const [showNotifs, setShowNotifs] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
        <DropdownMenuContent className="w-56" align="end" sideOffset={8}>
          <DropdownMenuLabel>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">{user?.display_name || 'User'}</p>
              <p className="text-xs text-muted-foreground">{user?.email || ''}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Profile</DropdownMenuItem>
          <DropdownMenuItem>Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={logout}>
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
