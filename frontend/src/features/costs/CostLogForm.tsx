import { useState, useRef } from 'react'
import { DollarSign, Upload, X, CheckCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { CostCategory, PaymentMethod, CostCurrency } from '@/types'

// ── Consts ──────────────────────────────────────────────────────────────────

const CATEGORIES: { value: CostCategory; label: string }[] = [
  { value: 'fuel', label: 'Fuel' },
  { value: 'handling', label: 'Handling' },
  { value: 'landing', label: 'Landing' },
  { value: 'customs', label: 'Customs' },
  { value: 'parking', label: 'Parking' },
  { value: 'misc', label: 'Misc' },
]

const CURRENCIES: CostCurrency[] = ['USD', 'EUR', 'GBP', 'HTG', 'CUP', 'DOP', 'MXN']

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'credit', label: 'Credit' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'wire', label: 'Wire' },
]

// ── Form State ──────────────────────────────────────────────────────────────

interface FormState {
  category: CostCategory
  amount: string
  currency: CostCurrency
  payment_method: PaymentMethod
  notes: string
  logged_by: string
}

interface CostLogFormProps {
  legNumber: number
  departureAirport: string
  arrivalAirport: string
  loggedByDefault: string
  onSubmit: (data: {
    category: CostCategory
    amount: number
    currency: CostCurrency
    payment_method: PaymentMethod
    notes?: string
    receipt_url?: string
  }) => Promise<void>
}

// ── Styled select (reusable since shadcn/ui Select not installed) ───────────

function StyledSelect({
  value,
  onChange,
  options,
  label,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  label: string
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted-foreground">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function CurrencySelect({
  value,
  onChange,
}: {
  value: CostCurrency
  onChange: (v: CostCurrency) => void
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted-foreground">Currency</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as CostCurrency)}
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {CURRENCIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </div>
  )
}

// ── Component ───────────────────────────────────────────────────────────────

export default function CostLogForm({
  legNumber,
  departureAirport,
  arrivalAirport,
  loggedByDefault,
  onSubmit,
}: CostLogFormProps) {
  const [form, setForm] = useState<FormState>({
    category: 'fuel',
    amount: '',
    currency: 'USD',
    payment_method: 'credit_card',
    notes: '',
    logged_by: loggedByDefault,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [receiptFile, setReceiptFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const update = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    setError('')
    setSuccess(false)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setReceiptFile(file)
  }

  const clearFile = () => {
    setReceiptFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const amount = parseFloat(form.amount)
    if (isNaN(amount) || amount <= 0) {
      setError('Please enter a valid amount greater than 0.')
      return
    }
    setSubmitting(true)
    setError('')
    setSuccess(false)
    try {
      await onSubmit({
        category: form.category,
        amount,
        currency: form.currency,
        payment_method: form.payment_method,
        notes: form.notes || undefined,
        receipt_url: receiptFile ? `receipt_placeholder_${legNumber}_${Date.now()}` : undefined,
      })
      setSuccess(true)
      // Reset form (keep category, currency, payment defaults)
      setForm({
        category: 'fuel',
        amount: '',
        currency: 'USD',
        payment_method: 'credit_card',
        notes: '',
        logged_by: loggedByDefault,
      })
      clearFile()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to log cost. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Route context */}
      <p className="text-xs text-muted-foreground">
        Leg {legNumber}: {departureAirport} → {arrivalAirport}
      </p>

      {/* Category + Amount row — stack on mobile */}
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <div className="flex-1">
          <StyledSelect
            label="Category"
            value={form.category}
            onChange={(v) => update('category', v)}
            options={CATEGORIES}
          />
        </div>
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Amount <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <DollarSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0.00"
              value={form.amount}
              onChange={(e) => update('amount', e.target.value)}
              className="pl-9"
              required
            />
          </div>
        </div>
      </div>

      {/* Currency + Payment Method — stack on mobile */}
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <div className="flex-1">
          <CurrencySelect
            value={form.currency}
            onChange={(v) => update('currency', v)}
          />
        </div>
        <div className="flex-1">
          <StyledSelect
            label="Payment Method"
            value={form.payment_method}
            onChange={(v) => update('payment_method', v)}
            options={PAYMENT_METHODS}
          />
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Notes</label>
        <textarea
          value={form.notes}
          onChange={(e) => update('notes', e.target.value)}
          placeholder="Optional notes about this cost..."
          rows={2}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>

      {/* Receipt upload */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Receipt (V1 — placeholder)</label>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5"
          >
            <Upload className="h-3.5 w-3.5" />
            {receiptFile ? 'Change File' : 'Upload Receipt'}
          </Button>
          {receiptFile && (
            <div className="flex items-center gap-2 rounded-md bg-muted/20 px-2 py-1 text-xs">
              <span className="max-w-[160px] truncate text-muted-foreground">{receiptFile.name}</span>
              <button
                type="button"
                onClick={clearFile}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      </div>

      {/* Logged by */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Logged by</label>
        <Input
          value={form.logged_by}
          onChange={(e) => update('logged_by', e.target.value)}
          placeholder="Your name"
          className="w-full"
        />
      </div>

      {/* Feedback */}
      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 p-2 text-xs text-red-500">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="flex items-start gap-2 rounded-md border border-green-500/20 bg-green-500/5 p-2 text-xs text-green-500">
          <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>Cost logged successfully!</span>
        </div>
      )}

      {/* Submit */}
      <Button type="submit" disabled={submitting} className="w-full sm:w-auto">
        <DollarSign className="mr-1.5 h-4 w-4" />
        {submitting ? 'Logging...' : 'Log Actual Cost'}
      </Button>
    </form>
  )
}
