import type {
  Case,
  Recommendation,
  AuditEvent,
  DashboardMetrics,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface CaseListResponse {
  cases: Case[];
  total: number;
  page: number;
  page_size: number;
}

interface CaseCreate {
  title: string;
  description: string;
  priority?: string;
  issue_type?: string;
  transaction_id?: string;
  account_id?: string;
  merchant_name?: string;
  merchant_ref?: string;
  amount?: number;
  currency?: string;
}

interface CaseUpdate {
  title?: string;
  description?: string;
  priority?: string;
  assigned_to?: string;
}

interface CaseNote {
  id: string;
  case_id: string;
  author_id: string;
  content: string;
  note_type: string;
  created_at: string;
}

interface NoteCreate {
  content: string;
  note_type?: string;
}

interface AnalystAction {
  action_type: string;
  recommendation_id?: string | null;
  reason?: string;
}

interface StatusHistory {
  id: string;
  case_id: string;
  from_status: string | null;
  to_status: string;
  changed_by: string;
  reason: string | null;
  created_at: string;
}

interface WorkflowResult {
  case_id: string;
  status: string;
  steps: Record<string, unknown>[];
  trace_id: string;
  total_duration_ms: number;
  recommendation: Record<string, unknown> | null;
  citations_count: number;
  tools_executed: number;
}

interface WorkflowStates {
  states: string[];
  transitions: Record<string, string[]>;
}

interface PolicyDocument {
  id: string;
  title: string;
  category: string;
  version: string;
  content: string | null;
  created_at: string;
}

interface ToolExecuteRequest {
  tool_name: string;
  params: Record<string, unknown>;
}

interface HealthResponse {
  status: string;
  services: Record<string, string>;
}

interface AuditListResponse {
  events: AuditEvent[];
  total: number;
}

interface ToolInvocationRecord {
  id: string;
  case_id: string;
  tool_name: string;
  tool_type: string;
  status: string;
  duration_ms: number;
  created_at: string;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  cases: {
    list: (params?: Record<string, string>) => {
      const query = params ? "?" + new URLSearchParams(params).toString() : "";
      return fetchAPI<CaseListResponse>(`/api/v1/cases${query}`);
    },
    get: (id: string) => fetchAPI<Case>(`/api/v1/cases/${id}`),
    create: (data: CaseCreate) =>
      fetchAPI<Case>("/api/v1/cases", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: CaseUpdate) =>
      fetchAPI<Case>(`/api/v1/cases/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    history: (id: string) => fetchAPI<StatusHistory[]>(`/api/v1/cases/${id}/history`),
    recommendations: (id: string) =>
      fetchAPI<Recommendation[]>(`/api/v1/cases/${id}/recommendations`),
    notes: (id: string) => fetchAPI<CaseNote[]>(`/api/v1/cases/${id}/notes`),
    addNote: (id: string, data: NoteCreate) =>
      fetchAPI<CaseNote>(`/api/v1/cases/${id}/notes`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    action: (id: string, data: AnalystAction) =>
      fetchAPI<Record<string, unknown>>(`/api/v1/cases/${id}/actions`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  policies: {
    list: () => fetchAPI<PolicyDocument[]>("/api/v1/policies"),
    get: (id: string) => fetchAPI<PolicyDocument>(`/api/v1/policies/${id}`),
  },
  tools: {
    execute: (data: ToolExecuteRequest) =>
      fetchAPI<Record<string, unknown>>("/api/v1/tools/execute", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  workflow: {
    run: (caseId: string) =>
      fetchAPI<WorkflowResult>("/api/v1/workflow/run", {
        method: "POST",
        body: JSON.stringify({ case_id: caseId }),
      }),
    states: () => fetchAPI<WorkflowStates>("/api/v1/workflow/states"),
  },
  audit: {
    list: (params?: Record<string, string>) => {
      const query = params ? "?" + new URLSearchParams(params).toString() : "";
      return fetchAPI<AuditListResponse>(`/api/v1/audit${query}`);
    },
    tools: (params?: Record<string, string>) => {
      const query = params ? "?" + new URLSearchParams(params).toString() : "";
      return fetchAPI<ToolInvocationRecord[]>(`/api/v1/audit/tools${query}`);
    },
  },
  metrics: {
    dashboard: () => fetchAPI<DashboardMetrics>("/api/v1/metrics/dashboard"),
    evaluations: () => fetchAPI<Record<string, unknown>>("/api/v1/metrics/evaluations"),
    runEvaluation: () =>
      fetchAPI<Record<string, unknown>>("/api/v1/metrics/evaluations/run", { method: "POST" }),
  },
  prompts: {
    list: () => fetchAPI<Record<string, unknown>>("/api/v1/prompts"),
    get: (id: string) => fetchAPI<Record<string, unknown>>(`/api/v1/prompts/${id}`),
    active: (agentType: string) =>
      fetchAPI<Record<string, unknown>>(`/api/v1/prompts/active/${agentType}`),
    diff: (a: string, b: string) =>
      fetchAPI<Record<string, unknown>>(`/api/v1/prompts/diff/${a}/${b}`),
  },
  health: {
    check: () => fetchAPI<HealthResponse>("/health"),
  },
};
