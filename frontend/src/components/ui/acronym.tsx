import type { ReactNode } from 'react'
import ACRONYMS from '@/lib/acronyms'

interface AcronymProps {
  /** The acronym text to explain (case-insensitive lookup). */
  children: string
  /** Optional explicit definition — overrides the dictionary lookup. */
  title?: string
  /** Optional class override */
  className?: string
}

/**
 * Hover over any aviation acronym to see its definition.
 *
 * Usage:
 *   <Acronym>PIC</Acronym>          → lookup from dictionary
 *   <Acronym title="My custom def">FOOBAR</Acronym>  → explicit definition
 *
 * For inline text that contains acronyms, use <AcronymSpan>.
 */
export function Acronym({ children, title, className = '' }: AcronymProps) {
  const key = children.trim().toUpperCase()
  const definition = title || ACRONYMS[key]
  if (!definition) return <>{children}</>

  return (
    <span
      className={`cursor-help border-b border-dotted border-foreground/30 ${className}`}
      title={definition}
    >
      {children}
    </span>
  )
}

/**
 * Parse a string and wrap recognized acronyms in hover tooltips.
 * Anything matching a known acronym gets a dotted underline + hover definition.
 *
 * Usage:
 *   <AcronymSpan text="File with FAA for NOTAM access" />
 */
const ACRONYM_PATTERN = new RegExp(
  '\\b(' + Object.keys(ACRONYMS).map(escapeRegex).join('|') + ')\\b',
  'gi'
)

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function AcronymSpan({ text, className = '' }: { text: string; className?: string }) {
  const parts: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  const re = new RegExp(ACRONYM_PATTERN.source, 'gi')
  while ((match = re.exec(text)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    const key = match[0].toUpperCase()
    const def = ACRONYMS[key]
    if (def) {
      parts.push(
        <span
          key={match.index}
          className={`cursor-help border-b border-dotted border-foreground/30 ${className}`}
          title={def}
        >
          {match[0]}
        </span>
      )
    } else {
      parts.push(match[0])
    }
    lastIndex = re.lastIndex
  }

  // Remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return <>{parts}</>
}
