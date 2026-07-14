import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function FlightsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Flights</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Schedule and track charter flights (Nassau ↔ Haiti routes)
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Flight Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border">
            <p className="text-sm text-muted-foreground">
              Flight scheduling interface will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
