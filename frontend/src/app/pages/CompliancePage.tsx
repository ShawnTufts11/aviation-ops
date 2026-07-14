import { useState, useEffect, type FormEvent } from 'react'
import { ShieldCheck, Plus, Upload, AlertTriangle, Clock, FileText, Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import api from '@/lib/api'

interface Document {
  id: string
  title: string
  doc_type: string
  doc_number: string | null
  issuing_authority: string | null
  issue_date: string | null
  expiry_date: string | null
  status: string
  aircraft_id: string | null
  crew_id: string | null
  countries: string | null
  regulations: string | null
  notes: string | null
}

const DOC_TYPE_LABELS: Record<string, string> = {
  airworthiness_cert: 'Airworthiness Cert',
  registration: 'Registration',
  insurance: 'Insurance',
  operating_specs: 'Operating Specs',
  aoc: 'AOC',
  noise_cert: 'Noise Cert',
  landing_permit: 'Landing Permit',
  overflight_permit: 'Overflight Permit',
  crew_license: 'Crew License',
  medical: 'Medical',
  ops_manual: 'Ops Manual',
  mel: 'MEL',
}

const STATUS_COLORS: Record<string, string> = {
  current: 'bg-green-500/10 text-green-500',
  expiring_soon: 'bg-amber-500/10 text-amber-500',
  expired: 'bg-red-500/10 text-red-500',
  revoked: 'bg-muted text-muted-foreground',
}

export default function CompliancePage() {
  const [docs, setDocs] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [dashboard, setDashboard] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showAdd, setShowAdd] = useState(false)

  const [title, setTitle] = useState('')
  const [docType, setDocType] = useState('insurance')
  const [docNum, setDocNum] = useState('')
  const [authority, setAuthority] = useState('')
  const [issueDate, setIssueDate] = useState('')
  const [expiryDate, setExpiryDate] = useState('')
  const [countries, setCountries] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchData = async () => {
    try {
      const [docRes, dashRes] = await Promise.all([
        api.get('/api/v1/compliance/documents?per_page=50'),
        api.get('/api/v1/compliance/dashboard'),
      ])
      setDocs(docRes.data.data)
      setTotal(docRes.data.total)
      setDashboard(dashRes.data)
    } catch { /* silent */ }
  }

  useEffect(() => { fetchData() }, [])

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/v1/compliance/documents', {
        title, doc_type: docType,
        doc_number: docNum || undefined,
        issuing_authority: authority || undefined,
        issue_date: issueDate || undefined,
        expiry_date: expiryDate || undefined,
        countries: countries || undefined,
      })
      setShowAdd(false)
      setTitle(''); setDocNum(''); setAuthority(''); setIssueDate(''); setExpiryDate(''); setCountries('')
      await fetchData()
    } catch { /* silent */ }
    setSubmitting(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compliance</h1>
          <p className="mt-1 text-sm text-muted-foreground">{total} documents on file</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Document
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="all">All Documents ({total})</TabsTrigger>
          <TabsTrigger value="expiring" className="text-amber-500">Expiring</TabsTrigger>
          <TabsTrigger value="expired" className="text-red-500">Expired</TabsTrigger>
        </TabsList>

        {/* Dashboard */}
        <TabsContent value="dashboard" className="space-y-4">
          {dashboard && (
            <>
              <div className="grid gap-4 sm:grid-cols-4">
                <Card><CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-green-500">{dashboard.current_count}</p>
                  <p className="text-sm text-muted-foreground">Current</p>
                </CardContent></Card>
                <Card className="border-amber-500/30"><CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-amber-500">{dashboard.expiring_count}</p>
                  <p className="text-sm text-muted-foreground">Expiring Soon</p>
                </CardContent></Card>
                <Card className="border-red-500/30"><CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-red-500">{dashboard.expired_count}</p>
                  <p className="text-sm text-muted-foreground">Expired</p>
                </CardContent></Card>
                <Card><CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold">{dashboard.total}</p>
                  <p className="text-sm text-muted-foreground">Total</p>
                </CardContent></Card>
              </div>

              {/* By country */}
              {dashboard.by_country && Object.keys(dashboard.by_country).length > 0 && (
                <Card>
                  <CardContent className="p-4">
                    <p className="mb-2 text-sm font-medium flex items-center gap-2"><Globe className="h-4 w-4" /> Documents by Country</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(dashboard.by_country).map(([c, n]) => (
                        <Badge key={c} variant="outline">{c} ({n as number})</Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Expiring soon */}
              {dashboard.expiring_soon?.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-amber-500 flex items-center gap-2"><Clock className="h-4 w-4" /> Expiring Within 30 Days</h3>
                  <div className="space-y-2">
                    {dashboard.expiring_soon.map((d: Document) => (
                      <Card key={d.id} className="border-amber-500/20"><CardContent className="flex items-center justify-between p-3 text-sm">
                        <span className="font-medium">{d.title}</span>
                        <span className="text-muted-foreground">{d.expiry_date}</span>
                      </CardContent></Card>
                    ))}
                  </div>
                </div>
              )}

              {/* Expired */}
              {dashboard.expired?.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-red-500 flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> Expired Documents</h3>
                  <div className="space-y-2">
                    {dashboard.expired.map((d: Document) => (
                      <Card key={d.id} className="border-red-500/20"><CardContent className="flex items-center justify-between p-3 text-sm">
                        <span className="font-medium">{d.title}</span>
                        <span className="text-muted-foreground">{d.expiry_date}</span>
                      </CardContent></Card>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* All documents */}
        <TabsContent value={activeTab} className="mt-4">
          {docs.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border py-16">
              <ShieldCheck className="h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">No documents yet</p>
              <Button onClick={() => setShowAdd(true)}>
                <Plus className="mr-2 h-4 w-4" /> Add Document
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {(activeTab === 'expiring'
                ? docs.filter(d => d.status === 'expiring_soon' || (d.expiry_date && new Date(d.expiry_date) < new Date(Date.now() + 30*86400000)))
                : activeTab === 'expired'
                ? docs.filter(d => d.status === 'expired' || (d.expiry_date && new Date(d.expiry_date) < new Date()))
                : docs
              ).map((d) => {
                const color = STATUS_COLORS[d.status] || ''
                return (
                  <Card key={d.id} className="border-border/50">
                    <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{d.title}</span>
                          <Badge variant="outline" className={color}>{d.status.replace('_', ' ')}</Badge>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                          <span className="capitalize">{DOC_TYPE_LABELS[d.doc_type] || d.doc_type.replace(/_/g, ' ')}</span>
                          {d.doc_number && <span className="font-mono text-xs">{d.doc_number}</span>}
                          {d.issuing_authority && <span>{d.issuing_authority}</span>}
                          {d.expiry_date && <span>Expires: {d.expiry_date}</span>}
                          {d.countries && <span>{d.countries}</span>}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Document Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Document</DialogTitle>
            <DialogDescription>Track a compliance document.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Insurance Policy 2026" required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Type</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={docType} onChange={(e) => setDocType(e.target.value)}>
                  {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Doc #</label>
                <Input value={docNum} onChange={(e) => setDocNum(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Issuing Authority</label>
              <Input value={authority} onChange={(e) => setAuthority(e.target.value)} placeholder="BCAA / FAA" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Issue Date</label>
                <Input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Expiry Date</label>
                <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Countries (comma-separated)</label>
              <Input value={countries} onChange={(e) => setCountries(e.target.value.toUpperCase())} placeholder="BS, HT, US" />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>
                <Upload className="mr-2 h-4 w-4" />{submitting ? 'Saving...' : 'Add Document'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
