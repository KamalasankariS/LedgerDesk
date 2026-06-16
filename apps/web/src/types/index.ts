export interface Case {
  id: string;
  case_number: string;
  title: string;
  description: string;
  status: CaseStatus;
  priority: CasePriority;
  issue_type: string | null;
  transaction_id: string | null;
  account_id: string | null;
  merchant_name: string | null;
  merchant_ref: string | null;
  amount: number | null;
  currency: string;
  assigned_to: string | null;
  confidence_score: number | null;
  requires_human_review: boolean;
  trace_id: string | null;
  extracted_entities: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export type CaseStatus =
  | "created" | "triaged" | "context_retrieved" | "tools_selected"
  | "tools_executed" | "recommendation_generated" | "safety_checked"
  | "awaiting_review" | "approved" | "rejected" | "escalated"
  | "completed" | "failed_safe";

export type CasePriority = "low" | "medium" | "high" | "critical";

export interface Recommendation {
  id: string;
  case_id: string;
  recommended_action: string;
  rationale: string;
  confidence_score: number;
  policy_citations: Record<string, unknown>[] | null;
  evidence_summary: Record<string, unknown> | null;
  structured_decision: Record<string, unknown> | null;
  required_approval_level: string;
  analyst_summary: string | null;
  safety_gate_passed: boolean | null;
  safety_gate_details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  case_id: string | null;
  event_type: string;
  actor_type: "system" | "human";
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  trace_id: string | null;
  created_at: string;
}

export interface DashboardMetrics {
  total_cases: number;
  cases_by_status: Record<string, number>;
  cases_by_priority: Record<string, number>;
  analyst_actions: Record<string, number>;
  average_confidence: number | null;
  total_tool_invocations: number;
  average_tool_latency_ms: number | null;
  approval_rate: number | null;
  total_agent_runs: number;
  total_tokens: number;
  estimated_cost_usd: number;
}
