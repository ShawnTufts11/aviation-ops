import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function CrewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Crew</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage pilot and crew assignments
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Crew Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border">
            <p className="text-sm text-muted-foreground">
              Crew management interface will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
