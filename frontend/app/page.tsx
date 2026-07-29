'use client'
import { useState, useRef } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type HistoryItem = { question: string; answer: string }

function parseStep(raw: string): { agent: string; detail: string } {
  const idx = raw.indexOf(':')
  if (idx === -1) return { agent: raw, detail: '' }
  return { agent: raw.slice(0, idx).trim(), detail: raw.slice(idx + 1).trim() }
}

export default function Home() {
  const [question, setQuestion] = useState('')
  const [steps, setSteps] = useState<string[]>([])
  const [answer, setAnswer] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const esRef = useRef<EventSource | null>(null)

  const ask = () => {
    if (!question.trim() || loading) return
    const currentQuestion = question
    setLoading(true)
    setSteps([])
    setAnswer('')
    setAskedQuestion(currentQuestion)
    setQuestion('')

    const url = `${API_BASE}/chat/stream?question=${encodeURIComponent(currentQuestion)}&session_id=default`
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('step', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setSteps(prev => [...prev, data.step])
    })

    es.addEventListener('done', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setAnswer(data.answer)
      setHistory(prev => [...prev, { question: currentQuestion, answer: data.answer }])
      setLoading(false)
      es.close()
    })

    es.onerror = () => {
      setLoading(false)
      es.close()
    }
  }

  return (
    <main style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', padding: '64px 20px' }}>
      <div style={{ width: '100%', maxWidth: 680 }}>

        <div style={{ marginBottom: 40 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.16em',
            color: 'var(--signal)', textTransform: 'uppercase', marginBottom: 10,
          }}>
            ● agent console
          </div>
          <h1 style={{
            fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 32,
            margin: 0, letterSpacing: '-0.01em',
          }}>
            Multi-Agent AI Analyst
          </h1>
          <p style={{ color: 'var(--console-muted)', marginTop: 8, fontSize: 15, lineHeight: 1.5 }}>
            Ask about customers, orders, company policy, or general facts —
            routed live to the right specialist agent.
          </p>
        </div>

        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          background: 'var(--console-surface)', border: '1px solid var(--console-border)',
          borderRadius: 10, padding: '4px 4px 4px 16px', marginBottom: 28,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--signal)', fontSize: 15 }}>{'>'}</span>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && ask()}
            placeholder="How many customers have churned in the last 90 days?"
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--console-text)', fontFamily: 'var(--font-mono)', fontSize: 14.5,
              padding: '12px 0',
            }}
          />
          <button
            onClick={ask}
            disabled={loading}
            style={{
              padding: '10px 18px', borderRadius: 7, border: 'none',
              background: loading ? '#33394a' : 'var(--signal)',
              color: loading ? 'var(--console-muted)' : '#0a1a17',
              fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14,
              cursor: loading ? 'default' : 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {loading ? 'Working…' : 'Ask'}
          </button>
        </div>

        {(steps.length > 0 || loading) && (
          <div style={{
            background: 'var(--console-surface)', border: '1px solid var(--console-border)',
            borderRadius: 10, padding: '18px 20px', marginBottom: 20,
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '0.12em',
              color: 'var(--console-muted)', textTransform: 'uppercase', marginBottom: 14,
            }}>
              trace
            </div>
            <div style={{ position: 'relative', paddingLeft: 18 }}>
              <div style={{
                position: 'absolute', left: 4, top: 6, bottom: loading ? 0 : 6,
                width: 1, background: 'var(--console-border)',
              }} />
              {steps.map((s, i) => {
                const { agent, detail } = parseStep(s)
                const isCritic = agent.toLowerCase() === 'critic'
                const failed = isCritic && detail.toUpperCase().startsWith('FAIL')
                const dotColor = failed ? 'var(--warn)' : isCritic ? 'var(--ok)' : 'var(--signal)'
                return (
                  <div key={i} className="step-in" style={{ position: 'relative', marginBottom: 12, fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                    <div style={{
                      position: 'absolute', left: -18, top: 4, width: 9, height: 9,
                      borderRadius: '50%', background: dotColor,
                    }} />
                    <span style={{ color: 'var(--console-text)', fontWeight: 500 }}>{agent}</span>
                    {detail && <span style={{ color: 'var(--console-muted)' }}>  {detail}</span>}
                  </div>
                )
              })}
              {loading && (
                <div style={{ position: 'relative', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--console-muted)' }}>
                  <div style={{
                    position: 'absolute', left: -18, top: 4, width: 9, height: 9,
                    borderRadius: '50%', background: 'var(--console-border)',
                  }} />
                  …
                </div>
              )}
            </div>
          </div>
        )}

        {answer && (
          <div className="report-in" style={{
            background: 'var(--paper)', color: 'var(--paper-ink)',
            borderRadius: 6, padding: '24px 26px', marginBottom: 32,
            boxShadow: '0 12px 28px rgba(0,0,0,0.35)',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
              borderBottom: '1px solid var(--paper-rule)', paddingBottom: 10, marginBottom: 14,
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '0.12em',
                textTransform: 'uppercase', color: '#8a7654',
              }}>
                analyst report
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: '#a39785' }}>
                {steps.length} step{steps.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14.5, marginBottom: 10, color: '#4a4438' }}>
              {askedQuestion}
            </div>
            <div style={{ fontSize: 15.5, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {answer}
            </div>
          </div>
        )}

        {history.length > 1 && (
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '0.12em',
              color: 'var(--console-muted)', textTransform: 'uppercase', marginBottom: 12,
            }}>
              earlier
            </div>
            {history.slice(0, -1).reverse().map((h, i) => (
              <div key={i} style={{ marginBottom: 16, opacity: 0.55 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14 }}>{h.question}</div>
                <div style={{ fontSize: 14, marginTop: 4, whiteSpace: 'pre-wrap', color: 'var(--console-muted)' }}>{h.answer}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
