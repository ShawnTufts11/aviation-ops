import { useState, type FormEvent } from 'react'
import { Building2, Upload, Key, CheckCircle, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

export default function AdminPage() {
  // Create Org
  const [orgName, setOrgName] = useState('')
  const [orgSlug, setOrgSlug] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminName, setAdminName] = useState('')
  const [result, setResult] = useState<any>(null)
  const [copied, setCopied] = useState(false)

  // Bulk Import
  const [importType, setImportType] = useState('passengers')
  const [importResult, setImportResult] = useState<any>(null)
  const [uploading, setUploading] = useState(false)

  const handleCreateOrg = async (e: FormEvent) => {
    e.preventDefault()
    try {
      const res = await api.post('/api/v1/admin/create-org', {
        org_name: orgName,
        org_slug: orgSlug,
        admin_email: adminEmail,
        admin_name: adminName,
      })
      setResult(res.data)
    } catch { /* silent */ }
  }

  const handleImport = async (e: FormEvent) => {
    e.preventDefault()
    const fileInput = document.getElementById('csv-file') as HTMLInputElement
    if (!fileInput?.files?.length) return
    setUploading(true)
    const form = new FormData()
    form.append('file', fileInput.files[0])
    try {
      const res = await api.post(`/api/v1/bulk-import/${importType}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setImportResult(res.data)
    } catch { /* silent */ }
    setUploading(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
        <p className="mt-1 text-sm text-muted-foreground">Create client organizations and import data</p>
      </div>

      <Tabs defaultValue="create-org">
        <TabsList>
          <TabsTrigger value="create-org"><Building2 className="mr-2 h-4 w-4" /> Create Org</TabsTrigger>
          <TabsTrigger value="bulk-import"><Upload className="mr-2 h-4 w-4" /> Bulk Import</TabsTrigger>
          <TabsTrigger value="invite-codes"><Key className="mr-2 h-4 w-4" /> Invite Codes</TabsTrigger>
        </TabsList>

        {/* Create Org */}
        <TabsContent value="create-org" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">New Client Organization</CardTitle></CardHeader>
            <CardContent>
              {!result ? (
                <form onSubmit={handleCreateOrg} className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Organization Name</label>
                      <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">URL Slug</label>
                      <Input value={orgSlug} onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))} required />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Admin Name</label>
                      <Input value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Admin Email</label>
                      <Input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
                    </div>
                  </div>
                  <Button type="submit">Create Organization</Button>
                </form>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-md border border-green-500/20 bg-green-500/5 p-4">
                    <p className="flex items-center gap-2 text-sm text-green-500">
                      <CheckCircle className="h-4 w-4" /> Organization created
                    </p>
                  </div>
                  <div className="space-y-2 text-sm">
                    <p><span className="text-muted-foreground">Org: </span>{result.organization_name}</p>
                    <p><span className="text-muted-foreground">Admin: </span>{result.admin_email}</p>
                    <p><span className="text-muted-foreground">Invite code: </span></p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-sm">{result.invite_code}</code>
                      <Button variant="outline" size="sm" onClick={() => {
                        navigator.clipboard.writeText(result.invite_code)
                        setCopied(true)
                        setTimeout(() => setCopied(false), 2000)
                      }}>
                        <Copy className="mr-1 h-3.5 w-3.5" />{copied ? 'Copied!' : 'Copy'}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">Expires: {result.invite_expires}</p>
                  </div>
                  <Button variant="outline" onClick={() => { setResult(null); setOrgName(''); setOrgSlug(''); setAdminEmail(''); setAdminName('') }}>
                    Create Another
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Generate Invite Code</CardTitle></CardHeader>
            <CardContent>
              <InviteCodeGenerator />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Bulk Import */}
        <TabsContent value="bulk-import">
          <Card>
            <CardHeader><CardTitle className="text-base">CSV Import</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Import Type</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={importType} onChange={(e) => setImportType(e.target.value)}>
                  <option value="passengers">Passengers</option>
                  <option value="crew">Crew</option>
                  <option value="aircraft">Aircraft</option>
                </select>
              </div>
              <p className="text-xs text-muted-foreground">
                CSV required columns:<br />
                <strong>Passengers:</strong> full_name (optional: date_of_birth, gender, nationality, passport_number, email, phone, weight_kg)<br />
                <strong>Crew:</strong> first_name, last_name, email, role (optional: phone, license_type, license_number, base_airport)<br />
                <strong>Aircraft:</strong> tail_number, make, model (optional: year, max_seats, base)
              </p>
              <form onSubmit={handleImport}>
                <div className="flex items-center gap-3">
                  <Input id="csv-file" type="file" accept=".csv" required />
                  <Button type="submit" disabled={uploading}>
                    {uploading ? 'Importing...' : 'Import CSV'}
                  </Button>
                </div>
              </form>
              {importResult && (
                <div className="rounded-md border border-green-500/20 bg-green-500/5 p-3 text-sm text-green-500">
                  ✓ {importResult.imported} imported, {importResult.skipped} skipped
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Invite Codes */}
        <TabsContent value="invite-codes">
          <InviteCodeGenerator />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function InviteCodeGenerator() {
  const [role, setRole] = useState('admin')
  const [desc, setDesc] = useState('')
  const [code, setCode] = useState('')
  const [copied, setCopied] = useState(false)

  const generate = async () => {
    try {
      const res = await api.post('/api/v1/admin/invite-codes', {
        role,
        description: desc || undefined,
      })
      setCode(res.data.code)
    } catch { /* silent */ }
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="space-y-2">
          <label className="text-sm font-medium">Role</label>
          <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="admin">Admin</option>
            <option value="pilot">Pilot</option>
            <option value="dispatcher">Dispatcher</option>
            <option value="mechanic">Mechanic</option>
            <option value="ops_manager">Ops Manager</option>
          </select>
        </div>
        <div className="space-y-2 md:col-span-2">
          <label className="text-sm font-medium">Description (optional)</label>
          <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="E.g. 'Client XYZ onboarding'" />
        </div>
      </div>
      <Button onClick={generate}>Generate Code</Button>
      {code && (
        <div className="flex items-center gap-2">
          <code className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-sm">{code}</code>
          <Button variant="outline" size="sm" onClick={() => {
            navigator.clipboard.writeText(code)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
          }}>
            <Copy className="mr-1 h-3.5 w-3.5" />{copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      )}
    </div>
  )
}
