export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: {
    status: string;
    type?: string;
  };
  razorpay_integration?: {
    configured: boolean;
  };
}

export interface FactorExplanation {
  factor: string;
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;
  description: string;
}

export interface ScoringMetrics {
  recovery_score: number;
  recovery_probability: number;
  expected_recovery_value: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  factors?: FactorExplanation[];
}

export interface AIDecision {
  payment_id: string;
  action: 'RETRY' | 'PAYMENT_LINK' | 'WAIT' | 'STOP' | 'HUMAN_REVIEW';
  confidence: number;
  rationale: string;
  expected_recovery_value: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_delay_minutes: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  guardrail_notes?: string;
}

export interface GuardrailRuleEvaluation {
  rule_id: string;
  rule_name: string;
  status: 'ALLOW' | 'MODIFY' | 'BLOCK';
  severity: string;
  message: string;
}

export interface GuardrailResult {
  payment_id: string;
  original_action: 'RETRY' | 'PAYMENT_LINK' | 'WAIT' | 'STOP' | 'HUMAN_REVIEW';
  final_action: 'RETRY' | 'PAYMENT_LINK' | 'WAIT' | 'STOP' | 'HUMAN_REVIEW';
  status: 'ALLOW' | 'MODIFY' | 'BLOCK';
  rules_evaluated: string[];
  rules_triggered: string[];
  reason: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  requires_human_review: boolean;
  rule_details?: GuardrailRuleEvaluation[];
}

export interface PaymentLinkData {
  id: string;
  entity?: string;
  amount: number;
  currency: string;
  status: string;
  short_url: string;
  created_at?: number;
}

export interface RecoveryExecutionResponse {
  payment_id: string;
  guardrail_status: 'ALLOW' | 'MODIFY' | 'BLOCK';
  original_action: 'RETRY' | 'PAYMENT_LINK' | 'WAIT' | 'STOP' | 'HUMAN_REVIEW';
  final_action: 'RETRY' | 'PAYMENT_LINK' | 'WAIT' | 'STOP' | 'HUMAN_REVIEW';
  execution_status: 'EXECUTED_SUCCESS' | 'BLOCKED_BY_GUARDRAILS' | 'ESCALATED_FOR_HUMAN_REVIEW' | 'IDEMPOTENT_SKIPPED' | 'FAILED';
  payment_link?: PaymentLinkData | null;
  audit_id?: string;
  executed_at: string;
  message: string;
}

export interface PaymentItem {
  id?: number;
  payment_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  failure_reason: string;
  timestamp: string;
  status: string;
  previous_attempts: number;
  previous_recovery_attempts: number;
  time_since_failure_minutes: number;
  customer_success_rate: number;
  customer_lifetime_value: number;
  customer_previous_payments: number;
  recovery_score?: number;
  recovery_probability?: number;
  expected_recovery_value?: number;
}

export interface PaginatedPayments {
  items: PaymentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MetricsOverview {
  total_failed_payments: number;
  total_revenue_at_risk: number;
  average_payment_amount: number;
  payment_count_by_failure_reason: Record<string, number>;
  payment_count_by_payment_method: Record<string, number>;
  recovered_revenue_actual?: number;
  total_recovered_count?: number;
}

export interface PaymentFullDetail {
  payment_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  failure_reason: string;
  operational_status: string;
  previous_recovery_attempts: number;
  scoring: ScoringMetrics;
  ai_recommendation: AIDecision | null;
  guardrail_evaluation: GuardrailResult | null;
  attempts: Array<{
    attempt_id: string;
    attempt_number: number;
    action: string;
    status: string;
    response_payload?: PaymentLinkData | null;
    created_at: string;
  }>;
  audit_trail: Array<{
    log_id: string;
    event_type: string;
    actor: string;
    details?: any;
    created_at: string;
  }>;
}
