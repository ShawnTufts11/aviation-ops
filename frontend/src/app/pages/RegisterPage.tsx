import { Link } from 'react-router-dom'
import { PlaneTakeoff, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-4 flex items-center justify-center gap-2">
            <PlaneTakeoff className="h-8 w-8 text-brand-400" />
            <span className="text-2xl font-bold">ParaRig Ops</span>
          </div>
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10">
            <Lock className="h-6 w-6 text-amber-500" />
          </div>
          <CardTitle className="text-xl">Registration Disabled</CardTitle>
          <CardDescription>
            New organizations are created by invitation only. If you have an invite link, use it below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Link to="/login" className="block">
            <Button className="w-full">Sign In</Button>
          </Link>
          <p className="text-center text-xs text-muted-foreground">
            Already have an invite?{' '}
            <Link to="/accept-invite" className="text-brand-400 hover:underline">
              Accept your invite
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
