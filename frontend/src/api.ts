export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export interface DraftVersionOut {
  id: number;
  version_index: number;
  content: string;
  safety_score?: number | null;
  empathy_score?: number | null;
  created_at: string;
}

export interface ProtocolSessionListItem {
  id: number;
  intent: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProtocolSessionOut extends ProtocolSessionListItem {
  thread_id: string;
  latest_draft?: string | null;
  human_edited_draft?: string | null;
  final_protocol?: string | null;
  safety_score?: number | null;
  empathy_score?: number | null;
  iteration: number;
  drafts: DraftVersionOut[];
}

export interface BlackboardSnapshot {
  state: Record<string, unknown>;
  created_at?: string | null;
}

export type StreamEvent =
  | { type: 'agent_event'; payload: Record<string, unknown> }
  | { type: 'state'; payload: Record<string, unknown> }
  | { type: 'halt'; payload: { interrupts: unknown[] } };

export async function listSessions(): Promise<ProtocolSessionListItem[]> {
  const res = await fetch(`${API_BASE_URL}/protocols`);
  if (!res.ok) throw new Error('Failed to list sessions');
  return res.json();
}

export async function createSession(intent: string): Promise<ProtocolSessionOut> {
  try {
    console.log('API_BASE_URL:', API_BASE_URL);
    console.log('Creating session with intent:', intent);
    
    const res = await fetch(`${API_BASE_URL}/protocols`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent }),
    });
    
    console.log('Response status:', res.status);
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error('Error response:', errorText);
      throw new Error(`Failed to create session: ${res.status} ${errorText}`);
    }
    
    const data = await res.json();
    console.log('Session created:', data);
    return data;
  } catch (err) {
    console.error('createSession error:', err);
    throw err;
  }
}

export async function getSession(id: number): Promise<ProtocolSessionOut> {
  const res = await fetch(`${API_BASE_URL}/protocols/${id}`);
  if (!res.ok) throw new Error('Failed to get session');
  return res.json();
}

export async function getBlackboard(id: number): Promise<BlackboardSnapshot> {
  const res = await fetch(`${API_BASE_URL}/protocols/${id}/blackboard`);
  if (!res.ok) throw new Error('Failed to get blackboard state');
  return res.json();
}

export async function approveDraft(
  id: number,
  editedDraft: string,
): Promise<ProtocolSessionOut> {
  const res = await fetch(`${API_BASE_URL}/protocols/${id}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edited_draft: editedDraft }),
  });
  if (!res.ok) throw new Error('Failed to approve draft');
  return res.json();
}

export async function kickoffSession(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/protocols/${id}/kickoff`, {
    method: 'POST',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to kickoff session: ${res.status} ${text}`);
  }
}

export function openStartStream(
  id: number,
  onEvent: (evt: StreamEvent) => void,
): EventSource {
  const es = new EventSource(
    `${API_BASE_URL}/protocols/${id}/stream/start`,
  );

  es.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data) as StreamEvent;
      if (parsed && (parsed as any).type) {
        onEvent(parsed);
      }
    } catch {
      // ignore malformed events
    }
  };

  return es;
}

export function openResumeStream(
  id: number,
  onEvent: (evt: StreamEvent) => void,
): EventSource {
  const es = new EventSource(
    `${API_BASE_URL}/protocols/${id}/stream/resume`,
  );

  es.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data) as StreamEvent;
      if (parsed && (parsed as any).type) {
        onEvent(parsed);
      }
    } catch {
      // ignore malformed events
    }
  };

  return es;
}
