import { useState, useEffect } from 'react'
import { Clock, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthContext } from '@/features/auth/AuthContext'
import api from '@/lib/api'

export default function SettingsPage() {
  const { user } = useAuthContext()
  const [timeoutMins, setTimeoutMins] = useState('480')
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/v1/org/settings').then((res) => {
      setTimeoutMins(String(res.data.session_timeout_minutes))
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    const val = parseInt(timeoutMins)
    if (val < 30 || val > 480) return
    try {
      await api.patch('/api/v1/org/settings', { session_timeout_minutes: val })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch { /* silent */ }
  }

  const isSuperAdmin = user?.role === 'super_admin'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Organization configuration</p>
      </div>

      {loading ? (
        <div className="h-32 animate-pulse rounded-lg bg-muted" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4" />
                Session Timeout
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                How long before users are automatically logged out. Max 8 hours (480 minutes).
                Changes take effect on next login.
              </p>

              <div className="flex items-end gap-4">
                <div className="w-48 space-y-2">
                  <label htmlFor="timeout" className="text-sm font-medium">Timeout (minutes)</label>
                  <Input
                    id="timeout"
                    type="number"
                    min={30}
                    max={480}
                    value={timeoutMins}
                    onChange={(e) => setTimeoutMins(e.target.value)}
                    disabled={!isSuperAdmin}
                  />
                </div>
                <div className="text-sm text-muted-foreground">
                  = {Math.floor(parseInt(timeoutMins || '480') / 60)}h {parseInt(timeoutMins || '480') % 60}m
                </div>
              </div>

              {parseInt(timeoutMins || '480') > 480 && (
                <p className="text-sm text-red-500">Maximum is 480 minutes (8 hours)</p>
              )}
              {parseInt(timeoutMins || '480') < 30 && (
                <p className="text-sm text-amber-500">Minimum is 30 minutes</p>
              )}

              {isSuperAdmin ? (
                <Button onClick={handleSave} disabled={parseInt(timeoutMins || '480') > 480 || parseInt(timeoutMins || '480') < 30}>
                  <Save className="mr-2 h-4 w-4" />
                  {saved ? 'Saved!' : 'Save Settings'}
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">Only super admins can change this setting.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Current Session</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p><span className="text-muted-foreground">Logged in as: </span>{user?.display_name}</p>
              <p><span className="text-muted-foreground">Role: </span>{user?.role?.replace('_', ' ')}</p>
              <p><span className="text-muted-foreground">Session timeout: </span>{timeoutMins} minutes</p>
              <p className="text-xs text-muted-foreground">
                Changing the timeout requires re-login to take effect.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
