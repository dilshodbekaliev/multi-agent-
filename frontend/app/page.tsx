'use client'
import { useState, useRef, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type HistoryItem = { question: string; answer: string }
type EvalResult = { question: string; answer: string; faithfulness: number | null; answer_relevancy: number | null }
type EvalData = {
  available: boolean
  generated_at?: string
  results?: EvalResult[]
  averages?: { faithfulness: number | null; answer_relevancy: number | null }
}

const EXAMPLE_QUESTIONS = [
  { label: 'Why do customers churn?', agent: 'docs' },
  { label: 'How many customers churned this year?', agent: 'sql' },
  { label: "What's today's USD/UZS rate?", agent: 'web' },
  { label: 'Std deviation of 12, 45, 78, 34?', agent: 'code' },
]

function parseStep(raw: string): { agent: string; detail: string } {
  const idx = raw.indexOf(':')
  if (idx === -1) return { agent: raw, detail: '' }
  return { agent: raw.slice(0, idx).trim(), detail: raw.slice(idx + 1).trim() }
}

function scoreColor(score: number | null): string {
  if (score === null) return 'var(--console-muted)'
  if (score >= 0.8) return 'var(--ok)'
  if (score >= 0.5) return 'var(--warn)'
  return '#f45b69'
}

function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 6,
      border: '1px solid var(--console-border)', borderRadius: 999,
      padding: '5px 12px', fontFamily: 'var(--font-mono)', fontSize: 11.5,
    }}>
      <span style={{ color: 'var(--ok)', fontWeight: 600 }}>{value}</span>
      <span style={{ color: 'var(--console-muted)' }}>{label}</span>
    </div>
  )
}

function ChatView() {
  const [question, setQuestion] = useState('')
  const [steps, setSteps] = useState<string[]>([])
  const [answer, setAnswer] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const esRef = useRef<EventSource | null>(null)

  const ask = (overrideQuestion?: string) => {
    const q = overrideQuestion ?? question
    if (!q.trim() || loading) return
    setLoading(true)
    setSteps([])
    setAnswer('')
    setCopied(false)
    setAskedQuestion(q)
    setQuestion('')

    const url = `${API_BASE}/chat/stream?question=${encodeURIComponent(q)}&session_id=default`
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('step', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setSteps(prev => [...prev, data.step])
    })

    es.addEventListener('done', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setAnswer(data.answer)
      setHistory(prev => [...prev, { question: q, answer: data.answer }])
      setLoading(false)
      es.close()
    })

    es.onerror = () => {
      setLoading(false)
      es.close()
    }
  }

  const copyAnswer = () => {
    navigator.clipboard.writeText(answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const showChips = !loading && steps.length === 0 && !answer

  return (
    <>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--console-surface)', border: '1px solid var(--console-border)',
        borderRadius: 10, padding: '4px 4px 4px 16px', marginBottom: showChips ? 14 : 28,
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
          onClick={() => ask()}
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

      {showChips && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 28 }}>
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button
              key={i}
              className="chip"
              onClick={() => ask(q.label)}
              style={{
                background: 'var(--console-surface)', border: '1px solid var(--console-border)',
                borderRadius: 999, padding: '7px 14px', fontFamily: 'var(--font-mono)',
                fontSize: 12, color: 'var(--console-muted)', cursor: 'pointer',
              }}
            >
              {q.label}
            </button>
          ))}
        </div>
      )}

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
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: '#a39785' }}>
                {steps.length} step{steps.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={copyAnswer}
                style={{
                  background: 'transparent', border: '1px solid var(--paper-rule)', borderRadius: 5,
                  padding: '3px 9px', fontFamily: 'var(--font-mono)', fontSize: 10.5,
                  color: '#8a7654', cursor: 'pointer',
                }}
              >
                {copied ? 'copied' : 'copy'}
              </button>
            </div>
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
    </>
  )
}

function EvalView() {
  const [data, setData] = useState<EvalData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/eval`)
      .then(res => res.json())
      .then(setData)
      .catch(() => setData({ available: false }))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div style={{ color: 'var(--console-muted)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>Loading…</div>
  }

  if (!data?.available) {
    return (
      <div style={{
        background: 'var(--console-surface)', border: '1px solid var(--console-border)',
        borderRadius: 10, padding: 24, color: 'var(--console-muted)', fontSize: 14,
      }}>
        No evaluation results yet. Run <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--signal)' }}>python -m app.eval</code> on the backend to generate them.
      </div>
    )
  }

  const avgF = data.averages?.faithfulness ?? null
  const avgR = data.averages?.answer_relevancy ?? null

  return (
    <>
      <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
        <div style={{
          flex: 1, background: 'var(--console-surface)', border: '1px solid var(--console-border)',
          borderRadius: 10, padding: '18px 20px',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '0.12em', color: 'var(--console-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            avg faithfulness
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 32, color: scoreColor(avgF) }}>
            {avgF !== null ? avgF.toFixed(2) : '—'}
          </div>
        </div>
        <div style={{
          flex: 1, background: 'var(--console-surface)', border: '1px solid var(--console-border)',
          borderRadius: 10, padding: '18px 20px',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, letterSpacing: '0.12em', color: 'var(--console-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            avg answer relevancy
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 32, color: scoreColor(avgR) }}>
            {avgR !== null ? avgR.toFixed(2) : '—'}
          </div>
        </div>
      </div>

      {data.generated_at && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--console-muted)', marginBottom: 20 }}>
          last run: {new Date(data.generated_at).toLocaleString()}
        </div>
      )}

      {data.results?.map((r, i) => (
        <div key={i} style={{
          background: 'var(--console-surface)', border: '1px solid var(--console-border)',
          borderRadius: 10, padding: '16px 20px', marginBottom: 12,
        }}>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14.5, marginBottom: 8 }}>
            {r.question}
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--console-muted)', marginBottom: 12, lineHeight: 1.5 }}>
            {r.answer}
          </div>
          <div style={{ display: 'flex', gap: 20, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            <span>
              faithfulness: <b style={{ color: scoreColor(r.faithfulness) }}>{r.faithfulness !== null ? r.faithfulness.toFixed(2) : 'n/a'}</b>
            </span>
            <span>
              relevancy: <b style={{ color: scoreColor(r.answer_relevancy) }}>{r.answer_relevancy !== null ? r.answer_relevancy.toFixed(2) : 'n/a'}</b>
            </span>
          </div>
        </div>
      ))}
    </>
  )
}

function ArchNode({ x, y, w, h, label, sub, fill, stroke }: { x: number; y: number; w: number; h: number; label: string; sub?: string; fill: string; stroke: string }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} fill={fill} stroke={stroke} strokeWidth={1.2} />
      <text x={x + w / 2} y={y + h / 2 + (sub ? -4 : 4)} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="11.5" fontWeight={600} fill="var(--console-text)">
        {label}
      </text>
      {sub && (
        <text x={x + w / 2} y={y + h / 2 + 11} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9" fill="var(--console-muted)">
          {sub}
        </text>
      )}
    </g>
  )
}

function ArchitectureView() {
  const agentX = [20, 220, 420, 620]
  const agentLabels = [
    { label: 'RETRIEVER', sub: 'vector search' },
    { label: 'WEB SEARCH', sub: 'live results' },
    { label: 'SQL AGENT', sub: 'text-to-SQL' },
    { label: 'CODE AGENT', sub: 'sandboxed exec' },
  ]

  return (
    <>
      <p style={{ color: 'var(--console-muted)', fontSize: 14, lineHeight: 1.6, marginBottom: 20, maxWidth: 560 }}>
        The supervisor routes each question to one or more specialist agents — running in parallel
        when a question needs more than one source — before the synthesizer drafts an answer and the
        critic checks it against the evidence. Teal shows the path every question takes; amber shows
        the conditional revision loop, taken only when the critic finds an unsupported claim.
      </p>

      <div style={{
        background: 'var(--console-surface)', border: '1px solid var(--console-border)',
        borderRadius: 10, padding: '20px 16px', overflowX: 'auto',
      }}>
        <svg viewBox="0 0 760 470" style={{ width: '100%', minWidth: 620, height: 'auto' }}>
          {agentX.map((ax, i) => (
            <path
              key={`sa-${i}`}
              className="flow-path"
              d={`M380,62 L380,100 L${ax + 70},100 L${ax + 70},140`}
              fill="none" stroke="var(--signal)" strokeWidth={1.5} opacity={0.75}
            />
          ))}
          {agentX.map((ax, i) => (
            <path
              key={`as-${i}`}
              className="flow-path"
              d={`M${ax + 70},184 L${ax + 70},210 L380,210 L380,238`}
              fill="none" stroke="var(--signal)" strokeWidth={1.5} opacity={0.75}
            />
          ))}
          <path className="flow-path" d="M380,282 L380,318" fill="none" stroke="var(--signal)" strokeWidth={1.5} />
          <path className="flow-path" d="M380,362 L380,400" fill="none" stroke="var(--ok)" strokeWidth={1.5} />
          <path
            d="M310,340 L260,340 L260,260 L310,260"
            fill="none" stroke="var(--warn)" strokeWidth={1.3} strokeDasharray="4 4" opacity={0.85}
          />
          <text x={200} y={296} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9.5" fill="var(--warn)">
            revise
          </text>
          <text x={200} y={308} textAnchor="middle" fontFamily="var(--font-mono)" fontSize="9.5" fill="var(--warn)">
            (≤2×)
          </text>

          <ArchNode x={310} y={18} w={140} h={44} label="SUPERVISOR" sub="routes the question" fill="var(--console-bg)" stroke="var(--signal)" />
          {agentX.map((ax, i) => (
            <ArchNode key={i} x={ax} y={140} w={140} h={44} label={agentLabels[i].label} sub={agentLabels[i].sub} fill="var(--console-bg)" stroke="var(--console-border)" />
          ))}
          <ArchNode x={310} y={238} w={140} h={44} label="SYNTHESIZER" sub="drafts the answer" fill="var(--console-bg)" stroke="var(--console-border)" />
          <ArchNode x={310} y={318} w={140} h={44} label="CRITIC" sub="checks the evidence" fill="var(--console-bg)" stroke="var(--console-border)" />
          <ArchNode x={320} y={402} w={120} h={38} label="ANSWER" fill="var(--paper)" stroke="var(--paper-rule)" />
        </svg>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 16, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--console-muted)' }}>
        <span><span style={{ color: 'var(--signal)' }}>●</span> always taken</span>
        <span><span style={{ color: 'var(--ok)' }}>●</span> critic passed</span>
        <span><span style={{ color: 'var(--warn)' }}>●</span> conditional revision</span>
      </div>
    </>
  )
}

export default function Home() {
  const [tab, setTab] = useState<'chat' | 'eval' | 'arch'>('chat')

  return (
    <main style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', padding: '64px 20px' }}>
      <div style={{ width: '100%', maxWidth: 720 }}>

        <div style={{ marginBottom: 20 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 7,
            fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.16em',
            color: 'var(--signal)', textTransform: 'uppercase', marginBottom: 10,
          }}>
            <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--signal)', display: 'inline-block' }} />
            agent console
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
          <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
            <StatBadge label="faithfulness" value="0.96" />
            <StatBadge label="answer relevancy" value="0.99" />
            <StatBadge label="specialist agents" value="4" />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 4, marginBottom: 28, borderBottom: '1px solid var(--console-border)' }}>
          {(['chat', 'eval', 'arch'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '10px 4px', marginRight: 20,
                fontFamily: 'var(--font-mono)', fontSize: 12.5, letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: tab === t ? 'var(--signal)' : 'var(--console-muted)',
                borderBottom: tab === t ? '2px solid var(--signal)' : '2px solid transparent',
                marginBottom: -1,
              }}
            >
              {t === 'chat' ? 'Chat' : t === 'eval' ? 'Evaluation' : 'Architecture'}
            </button>
          ))}
        </div>

        {tab === 'chat' ? <ChatView /> : tab === 'eval' ? <EvalView /> : <ArchitectureView />}
      </div>
    </main>
  )
}
