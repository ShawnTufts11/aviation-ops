import { useState, useRef, useEffect, type FormEvent } from 'react'
import { MessageSquare, Send, X, Bot, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import api from '@/lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const WELCOME_MSG: Message = {
  role: 'assistant',
  content: "Hi! I can help you with your operations. Try asking:\n\n• \"How many aircraft do I have?\"\n• \"List my fleet\"\n• \"When was the last oil change on C6-PRD?\"\n• \"Fleet summary\"",
  timestamp: new Date(),
}

function formatAnswer(text: string): string {
  // Bold
  let formatted = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // Newlines to breaks
  formatted = formatted.replace(/\n/g, '<br>')
  // Bullet points
  formatted = formatted.replace(/^\s*•\s*/gm, '&nbsp;&nbsp;• ')
  return formatted
}

export default function HelpdeskFloatingButton() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.post('/api/v1/helpdesk/ask', { question: userMsg.content })
      const botMsg: Message = {
        role: 'assistant',
        content: res.data.answer,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
        },
      ])
    }
    setLoading(false)
  }

  return (
    <>
      {/* Floating button */}
      <div className="fixed bottom-6 right-6 z-40">
        <Button
          onClick={() => setOpen(true)}
          className="h-14 w-14 rounded-full bg-brand-600 shadow-lg hover:bg-brand-700"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      </div>

      {/* Chat sheet */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-md">
          <SheetHeader className="border-b border-border px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-brand-400" />
                <SheetTitle className="text-base">AI Help Desk</SheetTitle>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </SheetHeader>

          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600/20">
                    <Bot className="h-4 w-4 text-brand-400" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-brand-600 text-white'
                      : 'bg-muted text-foreground'
                  }`}
                >
                  <div dangerouslySetInnerHTML={{ __html: formatAnswer(msg.content) }} />
                </div>
                {msg.role === 'user' && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600/20">
                  <Bot className="h-4 w-4 text-brand-400" />
                </div>
                <div className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                  <span className="animate-pulse">Thinking</span>
                  <span className="animate-pulse">.</span>
                  <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>.</span>
                  <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>.</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t border-border p-4">
            <div className="flex gap-2">
              <Input
                placeholder="Ask about your operations..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </>
  )
}
