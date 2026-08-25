import { useState, useEffect, useCallback } from 'react'
import { DollarSign, ChevronDown, ChevronRight, RefreshCw, Receipt, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAuthContext } from '@/features/auth/AuthContext'
import { fetchMissionCosts, fetchMissionPnl, logLegCost } from './api'
import CostLogForm from './CostLogForm'
import type {
  MissionCostsResponse,
  MissionPnlResponse,
  PerLegCosts,
  CostLogEntry,
  CostCategory,
} from '@/types'

interface CostsPnlSectionProps {
  missionId: string
  legs: { leg_number: number; departure_airport: string; arrival_airport: string }[]
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function fmtCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function pctColor(pct: number): string {
  if (pct > 10) return 'text-red-500'
  if (pct > 3) return 'text-amber-500'
  return 'text-green-500'
}

function statusBadge(variance: number, variancePct: number) {
  if (variancePct > 10 || variance > 500) {
    return <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">Over</Badge>
  }
  if (variancePct > 3 || variance > 100) {
    return <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20">Slight</Badge>
  }
  return <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">On Track</Badge>
}

function pnlStatusBadge(status: string) {
  if (status === 'under_budget') {
    return <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">Under Budget</Badge>
  }
  if (status === 'over_budget') {
    return <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">Over Budget</Badge>
  }
  return <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20">On Target</Badge>
}

const CATEGORY_LABELS: Record<CostCategory, string> = {
  fuel: 'Fuel',
  handling: 'Handling',
  landing: 'Landing',
  customs: 'Customs',
  parking: 'Parking',
  misc: 'Misc',
}

// ── Expanded Leg View ───────────────────────────────────────────────────────

function ExpandedLegView({
  leg,
  missionId,
  loggedByDefault,
  onCostLogged,
}: {
  leg: PerLegCosts
  missionId: string
  loggedByDefault: string
  onCostLogged: () => void
}) {
  return (
    <div className="space-y-3 pt-2">
      {/* Per-category breakdown */}
      {(leg?.breakdown?.length ?? 0) > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border/30 text-muted-foreground">
                <th className="py-1 pr-3 font-medium">Category</th>
                <th className="py-1 pr-3 font-medium">Amount</th>
                <th className="py-1 pr-3 font-medium">Currency</th>
                <th className="py-1 pr-3 font-medium">Payment</th>
                <th className="py-1 pr-3 font-medium">Notes</th>
                <th className="py-1 font-medium">By</th>
              </tr>
            </thead>
            <tbody>
              {leg.breakdown.map((entry) => (
                <tr key={entry.id} className="border-b border-border/10">
                  <td className="py-1 pr-3 font-medium">{CATEGORY_LABELS[entry.category] || entry.category}</td>
                  <td className="py-1 pr-3 font-mono">{fmtCurrency(entry.amount)}</td>
                  <td className="py-1 pr-3 text-muted-foreground">{entry.currency}</td>
                  <td className="py-1 pr-3 text-muted-foreground">{entry.payment_method.replace('_', ' ')}</td>
                  <td className="py-1 pr-3 max-w-[120px] truncate text-muted-foreground">{entry.notes || '—'}</td>
                  <td className="py-1 text-muted-foreground">{entry.logged_by}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {leg.breakdown.length === 0 && (
        <p className="text-xs text-muted-foreground italic">No costs logged yet for this leg.</p>
      )}

      {/* Variance summary per leg */}
      <div className="flex flex-wrap gap-3 rounded-md bg-muted/10 p-2 text-xs">
        <span>Est: <span className="font-mono">{fmtCurrency(leg.estimated_costs)}</span></span>
        <span>Actual: <span className="font-mono">{fmtCurrency(leg.actual_costs)}</span></span>
        <span className={pctColor(leg.variance_pct)}>
          Variance: {leg.variance >= 0 ? '+' : ''}{fmtCurrency(leg.variance)} ({leg.variance >= 0 ? '+' : ''}{leg.variance_pct.toFixed(1)}%)
        </span>
      </div>

      {/* Cost Log Form */}
      <div className="border-t border-border/30 pt-3">
        <p className="mb-2 text-xs font-medium text-muted-foreground">Log a new cost for this leg:</p>
        <CostLogForm
          legNumber={leg.leg_number}
          departureAirport={leg.departure_airport}
          arrivalAirport={leg.arrival_airport}
          loggedByDefault={loggedByDefault}
          onSubmit={async (data) => {
            await logLegCost(missionId, leg.leg_number, data)
            onCostLogged()
          }}
        />
      </div>
    </div>
  )
}

// ── Main Component ──────────────────────────────────────────────────────────

export default function CostsPnlSection({ missionId, legs }: CostsPnlSectionProps) {
  const { user } = useAuthContext()
  const [costs, setCosts] = useState<MissionCostsResponse | null>(null)
  const [pnl, setPnl] = useState<MissionPnlResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedLeg, setExpandedLeg] = useState<number | null>(null)

  const loggedByName = user?.display_name || user?.email || 'Unknown'

  const loadData = useCallback(async () => {
    if (!missionId) return
    setLoading(true)
    setError('')
    try {
      const [costsData, pnlData] = await Promise.all([
        fetchMissionCosts(missionId),
        fetchMissionPnl(missionId),
      ])
      setCosts(costsData)
      setPnl(pnlData)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load cost data.')
    } finally {
      setLoading(false)
    }
  }, [missionId])

  // Auto-load on mount
  useEffect(() => {
    loadData()
  }, [loadData])

  const toggleLeg = (legNumber: number) => {
    setExpandedLeg((prev) => (prev === legNumber ? null : legNumber))
  }

  // Merge backend leg costs with mission legs (so empty legs show up)
  const mergedLegs = legs.map((leg) => {
    const costLeg = costs?.legs?.find((cl) => cl.leg_number === leg.leg_number)
    if (costLeg) return { ...costLeg, breakdown: costLeg.breakdown ?? [] }
    return {
      leg_number: leg.leg_number,
      departure_airport: leg.departure_airport,
      arrival_airport: leg.arrival_airport,
      estimated_costs: 0,
      actual_costs: 0,
      variance: 0,
      variance_pct: 0,
      breakdown: [] as CostLogEntry[],
    }
  })

  const totalEstimated = costs?.total_estimated ?? 0
  const totalActual = costs?.total_actual ?? 0
  const totalVariance = costs?.total_variance ?? 0
  const totalVariancePct = totalEstimated > 0 ? (totalVariance / totalEstimated) * 100 : 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-brand-400" />
          Costs & P&amp;L
        </CardTitle>
        <div className="flex items-center gap-2">
          {error && <span className="text-xs text-red-500 max-w-[200px] truncate">{error}</span>}
          <Button
            variant="outline"
            size="sm"
            disabled={loading}
            onClick={loadData}
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {!costs && !error && loading && (
          <p className="text-sm text-muted-foreground italic">Loading cost data...</p>
        )}

        {error && !costs && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Could not load cost data</p>
              <p className="mt-1 text-xs opacity-80">{error}</p>
              <Button variant="outline" size="sm" onClick={loadData} className="mt-2">
                <RefreshCw className="mr-1.5 h-3 w-3" />
                Retry
              </Button>
            </div>
          </div>
        )}

        {costs && (
          <>
            {/* Per-leg summary */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="py-2 pr-2 font-medium w-8"></th>
                    <th className="py-2 pr-3 font-medium">Leg</th>
                    <th className="py-2 pr-3 font-medium">Route</th>
                    <th className="py-2 pr-3 font-medium text-right">Est.</th>
                    <th className="py-2 pr-3 font-medium text-right">Actual</th>
                    <th className="py-2 pr-3 font-medium text-right">Var.</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(mergedLegs || []).map((leg) => {
                    const isExpanded = expandedLeg === leg.leg_number
                    const pct = (leg?.estimated_costs ?? 0) > 0
                      ? ((leg.actual_costs - leg.estimated_costs) / leg.estimated_costs) * 100
                      : leg.actual_costs > 0 ? 100 : 0
                    return (
                      <tr key={leg.leg_number} className="border-b border-border/10">
                        <td className="py-2 pr-2">
                          <button
                            type="button"
                            onClick={() => toggleLeg(leg.leg_number)}
                            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
                          >
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                        </td>
                        <td className="py-2 pr-3 font-mono text-xs">{leg.leg_number}</td>
                        <td className="py-2 pr-3 font-medium">
                          <span className="hidden sm:inline">{leg.departure_airport} → {leg.arrival_airport}</span>
                          <span className="sm:hidden">{leg.departure_airport}→{leg.arrival_airport}</span>
                        </td>
                        <td className="py-2 pr-3 text-right font-mono text-xs">
                          {fmtCurrency(leg.estimated_costs)}
                        </td>
                        <td className="py-2 pr-3 text-right font-mono text-xs">
                          {(leg?.breakdown?.length ?? 0) > 0 ? fmtCurrency(leg.actual_costs) : '—'}
                        </td>
                        <td className={`py-2 pr-3 text-right font-mono text-xs ${pctColor(pct)}`}>
                          {(leg?.breakdown?.length ?? 0) > 0
                            ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
                            : '—'}
                        </td>
                        <td className="py-2">
                          {(leg?.breakdown?.length ?? 0) > 0 ? statusBadge(leg.variance, pct) : '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border/50 font-medium">
                    <td colSpan={2} className="py-2 pr-3"></td>
                    <td className="py-2 pr-3">Totals</td>
                    <td className="py-2 pr-3 text-right font-mono text-xs">
                      {fmtCurrency(totalEstimated)}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-xs">
                      {fmtCurrency(totalActual)}
                    </td>
                    <td className={`py-2 pr-3 text-right font-mono text-xs ${pctColor(totalVariancePct)}`}>
                      {totalVariance >= 0 ? '+' : ''}{totalVariancePct.toFixed(1)}%
                    </td>
                    <td className="py-2">{statusBadge(totalVariance, totalVariancePct)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Expanded leg detail */}
            {expandedLeg !== null && (
              <div className="mt-3 rounded-md border border-border/30 bg-muted/5 p-3">
                <ExpandedLegView
                  leg={mergedLegs.find((l) => l.leg_number === expandedLeg)!}
                  missionId={missionId}
                  loggedByDefault={loggedByName}
                  onCostLogged={loadData}
                />
              </div>
            )}

            {/* P&L Summary */}
            {pnl && (
              <div className="mt-4 rounded-md border border-border/50 bg-muted/10 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold flex items-center gap-1.5">
                    <Receipt className="h-4 w-4 text-brand-400" />
                    Mission P&amp;L Summary
                  </h4>
                  {pnlStatusBadge(pnl.status)}
                </div>

                {/* Top-level P&L */}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-md bg-background p-2 text-center">
                    <p className="text-xs text-muted-foreground">Total Estimated</p>
                    <p className="mt-1 text-lg font-bold font-mono">{fmtCurrency(pnl.total_estimated)}</p>
                  </div>
                  <div className="rounded-md bg-background p-2 text-center">
                    <p className="text-xs text-muted-foreground">Total Actual</p>
                    <p className="mt-1 text-lg font-bold font-mono">{fmtCurrency(pnl.total_actual)}</p>
                  </div>
                  <div className={`rounded-md bg-background p-2 text-center ${
                    pnl.total_variance > 0 ? 'text-red-500' : pnl.total_variance < 0 ? 'text-green-500' : ''
                  }`}>
                    <p className="text-xs text-muted-foreground">Variance</p>
                    <p className="mt-1 text-lg font-bold font-mono">
                      {pnl.total_variance >= 0 ? '+' : ''}{fmtCurrency(pnl.total_variance)}
                    </p>
                  </div>
                </div>

                {/* Per-category breakdown */}
                {pnl?.per_category?.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-1.5 text-xs font-medium text-muted-foreground">By Category</p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-border/30 text-muted-foreground">
                            <th className="py-1 pr-3 font-medium">Category</th>
                            <th className="py-1 pr-3 font-medium text-right">Est.</th>
                            <th className="py-1 pr-3 font-medium text-right">Actual</th>
                            <th className="py-1 font-medium text-right">Variance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pnl.per_category.map((cat) => {
                            const catPct = cat.estimated > 0
                              ? ((cat.actual - cat.estimated) / cat.estimated) * 100
                              : 0
                            return (
                              <tr key={cat.category} className="border-b border-border/10">
                                <td className="py-1 pr-3 font-medium">{CATEGORY_LABELS[cat.category] || cat.category}</td>
                                <td className="py-1 pr-3 text-right font-mono">{fmtCurrency(cat.estimated)}</td>
                                <td className="py-1 pr-3 text-right font-mono">{fmtCurrency(cat.actual)}</td>
                                <td className={`py-1 text-right font-mono ${pctColor(catPct)}`}>
                                  {cat.variance >= 0 ? '+' : ''}{fmtCurrency(cat.variance)}
                                  <span className="ml-1">({catPct >= 0 ? '+' : ''}{catPct.toFixed(1)}%)</span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!pnl && !error && !loading && (
              <p className="mt-4 text-sm text-muted-foreground italic">P&amp;L data not yet available.</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
