export type PlanStatus = 'draft' | 'ready' | 'archived';

export type PlanItemType =
  | 'transport'
  | 'activity'
  | 'food'
  | 'accommodation'
  | 'shopping'
  | 'service'
  | 'other';

export type ConstraintType =
  | 'budget_max'
  | 'budget_min'
  | 'time_max'
  | 'time_min'
  | 'distance_max'
  | 'group_size'
  | 'preference'
  | 'requirement';

export type CandidateType = 'place' | 'activity';

export type InformationCategory =
  | 'food'
  | 'culture'
  | 'nature'
  | 'entertainment'
  | 'wellness'
  | 'shopping';

export type ReasonType =
  | 'location'
  | 'budget'
  | 'group_size'
  | 'category'
  | 'duration'
  | 'general';

export type ReasonOutcome = 'supported' | 'neutral' | 'violated';

export interface DecisionReasonRead {
  type: ReasonType;
  outcome: ReasonOutcome;
  message: string;
}

export interface DecisionCandidateRead {
  option_id: string;
  option_type: CandidateType;
  name: string;
  is_eligible: boolean;
  score: number;
  reasons: DecisionReasonRead[];
  category: InformationCategory;
  cost: string | number | null;
  duration_minutes: number | null;
  location: string | null;
  source: string;
}

export interface RecommendationResponse {
  data_source: string;
  is_live: boolean;
  candidates: DecisionCandidateRead[];
}

export interface ContextRead {
  location: string | null;
  start_time: string | null;
  end_time: string | null;
  group_size: number;
  transport_mode: string | null;
}

export interface ConstraintRead {
  id: string;
  type: ConstraintType;
  value: string;
  numeric_value: string | number | null;
}

export interface PlanItemRead {
  id: string;
  name: string;
  item_type: PlanItemType;
  description: string | null;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number | null;
  estimated_cost: string | number | null;
  location: string | null;
  position: number;
}

export interface BudgetRead {
  budget_maximum: string | number | null;
  total_planned_cost: string | number;
  remaining_budget: string | number | null;
  is_over_budget: boolean;
}

export interface PlanRead {
  id: string;
  intention: string;
  title: string | null;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
  context: ContextRead | null;
  constraints: ConstraintRead[];
  items: PlanItemRead[];
  budget: BudgetRead;
}

export interface CreatePlanFromIntentRequest {
  request: string;
}

export interface SelectOptionRequest {
  option_id: string;
  option_type: CandidateType;
  position?: number | null;
  start_time?: string | null;
  end_time?: string | null;
}
