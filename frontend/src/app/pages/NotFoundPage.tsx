import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { PlaneTakeoff } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4">
      <div className="mb-6 flex items-center gap-2">
        <PlaneTakeoff className="h-8 w-8 text-brand-400" />
        <span className="text-2xl font-bold">ParaRig Ops</span>
      </div>
      <div className="text-center">
        <h1 className="text-8xl font-bold text-brand-500">404</h1>
        <h2 className="mt-4 text-2xl font-semibold text-foreground">
          Page Not Found
        </h2>
        <p className="mt-2 text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Button asChild className="mt-8">
          <Link to="/">Return to Dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
