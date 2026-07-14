import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  LayoutDashboard,
  Plane,
  MapPin,
  History,
  Wrench,
  Users,
  UserPlus,
  Shield,
  ShieldCheck,
  Wallet,
  Settings,
  ChevronLeft,
  ChevronRight,
  PlaneTakeoff,
} from 'lucide-react'

interface NavItem {
  label: string
  path: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <LayoutDashboard className="h-5 w-5" /> },
  { label: 'Fleet', path: '/fleet', icon: <Plane className="h-5 w-5" /> },
  { label: 'Missions', path: '/missions', icon: <MapPin className="h-5 w-5" /> },
  { label: 'Flights', path: '/flights', icon: <History className="h-5 w-5" /> },
  { label: 'Passengers', path: '/passengers', icon: <UserPlus className="h-5 w-5" /> },
  { label: 'Maintenance', path: '/maintenance', icon: <Wrench className="h-5 w-5" /> },
  { label: 'Crew', path: '/crew', icon: <Users className="h-5 w-5" /> },
  { label: 'Compliance', path: '/compliance', icon: <ShieldCheck className="h-5 w-5" /> },
  { label: 'Finance', path: '/finance', icon: <Wallet className="h-5 w-5" /> },
  { label: 'User Permissions', path: '/admin/users', icon: <Shield className="h-5 w-5" /> },
  { label: 'Admin Panel', path: '/admin', icon: <Settings className="h-5 w-5" /> },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'flex flex-col border-r border-sidebar-border bg-sidebar-background text-sidebar-foreground transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo Area */}
      <div
        className={cn(
          'flex h-16 items-center border-b border-sidebar-border px-4',
          collapsed ? 'justify-center' : 'justify-between',
        )}
      >
        {!collapsed && (
          <div className="flex items-center gap-2 overflow-hidden">
            <PlaneTakeoff className="h-6 w-6 shrink-0 text-brand-400" />
            <span className="truncate text-lg font-bold text-white">
              ParaRig Ops
            </span>
          </div>
        )}
        {collapsed && (
          <PlaneTakeoff className="h-6 w-6 shrink-0 text-brand-400" />
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className={cn(
            'hidden shrink-0 text-sidebar-foreground hover:text-white md:flex',
            collapsed && 'mt-2',
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                collapsed && 'justify-center px-2',
              )
            }
            title={collapsed ? item.label : undefined}
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {!collapsed && (
        <div className="px-4 py-3">
          <Separator className="mb-3 bg-sidebar-border" />
          <div className="text-xs text-sidebar-foreground/60">
            <p>Part 135 Ops</p>
            <p>v0.1.0</p>
          </div>
        </div>
      )}
    </aside>
  )
}
