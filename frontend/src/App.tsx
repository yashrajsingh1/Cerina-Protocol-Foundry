import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  listSessions,
  createSession,
  getSession,
  getBlackboard,
  approveDraft,
  openStartStream,
  openResumeStream,
} from './api';

interface Session {
  id: number;
  intent: string;
  status: string;
  created_at: string;
  updated_at: string;
  thread_id: string;
  latest_draft?: string;
  human_edited_draft?: string;
  final_protocol?: string;
  safety_score?: number;
  empathy_score?: number;
  iteration: number;
  drafts: Draft[];
}

interface Draft {
  id: number;
  version_index: number;
  content: string;
  safety_score?: number;
  empathy_score?: number;
  created_at: string;
}

interface AgentEvent {
  timestamp: string;
  agent: string;
  message: string;
}

const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [blackboard, setBlackboard] = useState<any>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [intentInput, setIntentInput] = useState('');
  const [draftText, setDraftText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isHalted, setIsHalted] = useState(false);
  const [streamSource, setStreamSource] = useState<EventSource | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const data = await listSessions();
        setSessions(data as any);
      } catch (err) {
        console.error('Failed to load sessions:', err);
      }
    };
    loadSessions();
    const interval = setInterval(loadSessions, 3000);
    return () => clearInterval(interval);
  }, []);

  // Load selected session details
  useEffect(() => {
    if (!selectedId) return;
    const loadSession = async () => {
      try {
        const session = await getSession(selectedId);
        setSelectedSession(session as any);
        setDraftText(session.latest_draft || '');
        setIsHalted(session.status === 'HALTED_FOR_HUMAN');
        const bb = await getBlackboard(selectedId);
        setBlackboard(bb.state);
      } catch (err) {
        console.error('Failed to load session:', err);
      }
    };
    loadSession();
  }, [selectedId]);

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const handleStreamEvent = useCallback((event: any) => {
    try {
      const data = JSON.parse(event.data);
      
      if (data.type === 'agent_event') {
        const newEvent: AgentEvent = {
          timestamp: new Date().toISOString(),
          agent: data.payload?.agent || 'Agent',
          message: data.payload?.event || 'Action',
        };
        setEvents((prev) => [newEvent, ...prev]);
      } else if (data.type === 'state') {
        setBlackboard(data.payload);
        if (data.payload?.current_draft) {
          setDraftText(data.payload.current_draft);
        }
      } else if (data.type === 'halt') {
        setIsHalted(true);
        setIsStreaming(false);
      }
    } catch (err) {
      console.error('Error parsing stream event:', err);
    }
  }, []);

  const handleStartAgents = useCallback(async () => {
    if (!selectedId || isStreaming) return;
    
    setIsStreaming(true);
    setEvents([]);
    setIsHalted(false);
    
    if (streamSource) streamSource.close();
    
    try {
      const es = openStartStream(selectedId, handleStreamEvent);
      setStreamSource(es);
    } catch (err) {
      console.error('Failed to start agents:', err);
      setIsStreaming(false);
    }
  }, [selectedId, isStreaming, streamSource, handleStreamEvent]);

  const handleApproveAndResume = useCallback(async () => {
    if (!selectedId || !isHalted) return;
    
    try {
      await approveDraft(selectedId, draftText);
      setIsStreaming(true);
      setIsHalted(false);
      
      if (streamSource) streamSource.close();
      const es = openResumeStream(selectedId, handleStreamEvent);
      setStreamSource(es);
    } catch (err) {
      console.error('Failed to approve and resume:', err);
    }
  }, [selectedId, isHalted, draftText, streamSource, handleStreamEvent]);

  const handleCreateSession = useCallback(async () => {
    if (!intentInput.trim()) {
      alert('Please enter an intent');
      return;
    }
    
    try {
      console.log('Creating session with intent:', intentInput.trim());
      const newSession = await createSession(intentInput.trim());
      console.log('Session created:', newSession);
      setSessions((prev) => [newSession as any, ...prev]);
      setSelectedId(newSession.id);
      setIntentInput('');
      setEvents([]);
      setBlackboard(null);
      setDraftText('');
      alert('Session created successfully!');
    } catch (err) {
      console.error('Failed to create session:', err);
      alert(`Error creating session: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [intentInput]);

  const safetyScore = blackboard?.safety_score;
  const empathyScore = blackboard?.empathy_score;
  const iteration = blackboard?.iteration ?? 0;

  return (
    <div style={styles.container}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h1 style={styles.title}>Cerina</h1>
          <p style={styles.subtitle}>Protocol Foundry</p>
        </div>

        <div style={styles.inputSection}>
          <label style={styles.label}>New Intent</label>
          <textarea
            value={intentInput}
            onChange={(e) => setIntentInput(e.target.value)}
            placeholder="e.g., Create an exposure hierarchy for agoraphobia"
            rows={4}
            style={styles.textarea}
          />
          <button
            onClick={handleCreateSession}
            disabled={!intentInput.trim()}
            style={{
              ...styles.button,
              ...styles.primaryButton,
              opacity: intentInput.trim() ? 1 : 0.5,
              cursor: intentInput.trim() ? 'pointer' : 'default',
            }}
          >
            Create Session
          </button>
        </div>

        <div style={styles.sessionsList}>
          <div style={styles.sessionsLabel}>Sessions ({sessions.length})</div>
          {sessions.length === 0 ? (
            <div style={styles.emptyState}>No sessions yet</div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedId(s.id)}
                style={{
                  ...styles.sessionItem,
                  ...(selectedId === s.id ? styles.sessionItemActive : {}),
                }}
              >
                <div style={styles.sessionIntent}>{s.intent}</div>
                <div style={styles.sessionMeta}>
                  {s.status} • {new Date(s.created_at).toLocaleDateString()}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main style={styles.main}>
        {/* Header */}
        <header style={styles.header}>
          <div>
            <div style={styles.headerLabel}>Selected Session</div>
            <div style={styles.headerTitle}>
              {selectedSession?.intent || 'No session selected'}
            </div>
          </div>
          <div style={styles.buttonGroup}>
            <button
              onClick={handleStartAgents}
              disabled={!selectedId || isStreaming || isHalted}
              style={{
                ...styles.button,
                ...styles.secondaryButton,
                opacity: !selectedId || isStreaming || isHalted ? 0.5 : 1,
                cursor: !selectedId || isStreaming || isHalted ? 'default' : 'pointer',
              }}
            >
              {isStreaming ? '⚙️ Running...' : 'Start Agents'}
            </button>
            <button
              onClick={handleApproveAndResume}
              disabled={!isHalted}
              style={{
                ...styles.button,
                ...styles.successButton,
                opacity: isHalted ? 1 : 0.5,
                cursor: isHalted ? 'pointer' : 'default',
              }}
            >
              {isHalted ? '✓ Approve & Resume' : 'Waiting...'}
            </button>
          </div>
        </header>

        {/* Content Grid */}
        <div style={styles.contentGrid}>
          {/* Left Column */}
          <div style={styles.leftColumn}>
            {/* Blackboard State */}
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <h2 style={styles.cardTitle}>Blackboard State</h2>
                <div style={styles.metrics}>
                  <span>Iter: <strong>{iteration}</strong></span>
                  <span>Safety: <strong>{safetyScore?.toFixed(1) ?? '-'}</strong></span>
                  <span>Empathy: <strong>{empathyScore?.toFixed(1) ?? '-'}</strong></span>
                </div>
              </div>
              <div style={styles.codeBlock}>
                {blackboard ? JSON.stringify(blackboard, null, 2) : 'No state yet. Start agents to see updates.'}
              </div>
            </div>

            {/* Draft Editor */}
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <h2 style={styles.cardTitle}>Draft (Human-in-the-Loop)</h2>
                <span style={{
                  ...styles.status,
                  color: isHalted ? '#d97706' : isStreaming ? '#2563eb' : '#6b7280',
                }}>
                  {isHalted ? '⚠️ Awaiting Approval' : isStreaming ? '⚙️ Running' : '✓ Idle'}
                </span>
              </div>
              <textarea
                value={draftText}
                onChange={(e) => setDraftText(e.target.value)}
                placeholder="Draft will appear here..."
                style={{
                  ...styles.draftTextarea,
                  backgroundColor: isHalted ? '#fffbeb' : '#f9fafb',
                }}
              />
              {isHalted && (
                <div style={styles.warningBox}>
                  ✏️ You can edit the draft. Click "Approve & Resume" when ready.
                </div>
              )}
            </div>
          </div>

          {/* Right Column */}
          <div style={styles.rightColumn}>
            {/* Agent Activity */}
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Agent Activity</h2>
              <div style={styles.eventsList}>
                {events.length === 0 ? (
                  <div style={styles.emptyState}>No events yet. Start agents to see activity.</div>
                ) : (
                  events.map((e, idx) => (
                    <div key={idx} style={styles.eventItem}>
                      <div style={styles.eventContent}>
                        <span style={styles.agentName}>{e.agent}</span>
                        <span style={styles.eventMessage}>{e.message}</span>
                      </div>
                      <div style={styles.eventTime}>
                        {new Date(e.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))
                )}
                <div ref={eventsEndRef} />
              </div>
            </div>

            {/* Version History */}
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Version History</h2>
              <div style={styles.versionsList}>
                {!selectedSession || selectedSession.drafts.length === 0 ? (
                  <div style={styles.emptyState}>No versions yet</div>
                ) : (
                  selectedSession.drafts.map((v) => (
                    <details key={v.id} style={styles.versionItem}>
                      <summary style={styles.versionSummary}>
                        v{v.version_index} • S: {v.safety_score?.toFixed(1) ?? '-'} E: {v.empathy_score?.toFixed(1) ?? '-'}
                      </summary>
                      <div style={styles.versionContent}>{v.content}</div>
                    </details>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    height: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    background: '#f3f4f6',
    color: '#1f2937',
  } as React.CSSProperties,

  sidebar: {
    width: 320,
    background: '#fff',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    overflow: 'hidden',
  } as React.CSSProperties,

  sidebarHeader: {
    padding: '24px 20px',
    borderBottom: '1px solid #e5e7eb',
  } as React.CSSProperties,

  title: {
    margin: '0 0 4px 0',
    fontSize: '28px',
    fontWeight: '700',
    color: '#059669',
  } as React.CSSProperties,

  subtitle: {
    margin: 0,
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '500',
  } as React.CSSProperties,

  inputSection: {
    padding: '20px',
    borderBottom: '1px solid #e5e7eb',
  } as React.CSSProperties,

  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px',
  } as React.CSSProperties,

  textarea: {
    width: '100%',
    padding: '10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontFamily: 'inherit',
    resize: 'vertical',
    boxSizing: 'border-box',
    marginBottom: '10px',
  } as React.CSSProperties,

  button: {
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  } as React.CSSProperties,

  primaryButton: {
    width: '100%',
    background: '#059669',
    color: 'white',
  } as React.CSSProperties,

  secondaryButton: {
    background: '#10b981',
    color: 'white',
  } as React.CSSProperties,

  successButton: {
    background: '#2563eb',
    color: 'white',
  } as React.CSSProperties,

  sessionsList: {
    flex: 1,
    overflow: 'auto',
    padding: '12px 0',
  } as React.CSSProperties,

  sessionsLabel: {
    padding: '12px 20px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#6b7280',
  } as React.CSSProperties,

  emptyState: {
    padding: '20px',
    textAlign: 'center',
    color: '#9ca3af',
    fontSize: '13px',
  } as React.CSSProperties,

  sessionItem: {
    width: '100%',
    padding: '12px 20px',
    textAlign: 'left',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    transition: 'background 0.2s',
    borderLeft: '3px solid transparent',
  } as React.CSSProperties,

  sessionItemActive: {
    background: '#f0fdf4',
    borderLeft: '3px solid #059669',
  } as React.CSSProperties,

  sessionIntent: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#1f2937',
    marginBottom: '4px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  } as React.CSSProperties,

  sessionMeta: {
    fontSize: '11px',
    color: '#6b7280',
  } as React.CSSProperties,

  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  } as React.CSSProperties,

  header: {
    padding: '20px 24px',
    borderBottom: '1px solid #e5e7eb',
    background: '#fff',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
  } as React.CSSProperties,

  headerLabel: {
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '500',
  } as React.CSSProperties,

  headerTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1f2937',
    marginTop: '4px',
  } as React.CSSProperties,

  buttonGroup: {
    display: 'flex',
    gap: '12px',
  } as React.CSSProperties,

  contentGrid: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '20px',
    padding: '20px 24px',
    overflow: 'hidden',
  } as React.CSSProperties,

  leftColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    minHeight: 0,
  } as React.CSSProperties,

  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    minHeight: 0,
  } as React.CSSProperties,

  card: {
    background: '#fff',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    padding: '20px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    minHeight: 0,
  } as React.CSSProperties,

  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  } as React.CSSProperties,

  cardTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '600',
    color: '#1f2937',
  } as React.CSSProperties,

  metrics: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#6b7280',
  } as React.CSSProperties,

  codeBlock: {
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '12px',
    fontSize: '12px',
    fontFamily: 'monospace',
    maxHeight: '150px',
    overflow: 'auto',
    color: '#374151',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  } as React.CSSProperties,

  draftTextarea: {
    flex: 1,
    width: '100%',
    padding: '12px',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    fontSize: '13px',
    fontFamily: 'monospace',
    resize: 'none',
    boxSizing: 'border-box',
    minHeight: 0,
  } as React.CSSProperties,

  warningBox: {
    marginTop: '12px',
    padding: '12px',
    background: '#fef3c7',
    border: '1px solid #fcd34d',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#92400e',
  } as React.CSSProperties,

  status: {
    fontSize: '12px',
    fontWeight: '500',
  } as React.CSSProperties,

  eventsList: {
    flex: 1,
    overflow: 'auto',
    fontSize: '12px',
    minHeight: 0,
  } as React.CSSProperties,

  eventItem: {
    paddingBottom: '12px',
    marginBottom: '12px',
    borderBottom: '1px solid #e5e7eb',
  } as React.CSSProperties,

  eventContent: {
    display: 'flex',
    gap: '8px',
    marginBottom: '4px',
  } as React.CSSProperties,

  agentName: {
    fontWeight: '600',
    color: '#059669',
  } as React.CSSProperties,

  eventMessage: {
    color: '#6b7280',
  } as React.CSSProperties,

  eventTime: {
    fontSize: '11px',
    color: '#9ca3af',
  } as React.CSSProperties,

  versionsList: {
    flex: 1,
    overflow: 'auto',
    fontSize: '12px',
    minHeight: 0,
  } as React.CSSProperties,

  versionItem: {
    marginBottom: '12px',
    paddingBottom: '12px',
    borderBottom: '1px solid #e5e7eb',
  } as React.CSSProperties,

  versionSummary: {
    cursor: 'pointer',
    fontWeight: '500',
    color: '#1f2937',
    marginBottom: '8px',
  } as React.CSSProperties,

  versionContent: {
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    padding: '8px',
    fontSize: '11px',
    fontFamily: 'monospace',
    maxHeight: '100px',
    overflow: 'auto',
    color: '#374151',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  } as React.CSSProperties,
};

export default App;
