import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plane, Users, Wrench, Wallet, TrendingUp, Calendar } from 'lucide-react'
import OnboardingWizard from '@/features/onboarding/OnboardingWizard'

const stats = [
  {
    label: 'Active Aircraft',
    value: '8',
    icon: Plane,
    badge: '4 en route',
    variant: 'info' as const,
  },
  {
    label: 'Today\'s Flights',
    value: '12',
    icon: TrendingUp,
    badge: '3 delayed',
    variant: 'warning' as const,
  },
  {
    label: 'Crew On Duty',
    value: '24',
    icon: Users,
    badge: '2 standby',
    variant: 'success' as const,
  },
  {
    label: 'Maintenance Due',
    value: '3',
    icon: Wrench,
    badge: '1 urgent',
    variant: 'destructive' as const,
  },
  {
    label: 'Revenue (MTD)',
    value: '$847K',
    icon: Wallet,
    badge: '+12.3%',
    variant: 'success' as const,
  },
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <OnboardingWizard />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Operation Center
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time overview of fleet operations
          </p>
        </div>
        <Badge variant="outline" className="gap-1 px-3 py-1">
          <Calendar className="h-3.5 w-3.5" />
          {new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </Badge>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="border-border/50">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.label}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <Badge variant={stat.variant} className="mt-1">
                  {stat.badge}
                </Badge>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Placeholder sections */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Flights</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border">
              <p className="text-sm text-muted-foreground">
                Flight data will appear here
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Fleet Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border">
              <p className="text-sm text-muted-foreground">
                Fleet overview will appear here
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-border">
            <p className="text-sm text-muted-foreground">
              Activity feed will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
