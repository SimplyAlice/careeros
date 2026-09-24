import { apiClient } from './client';
import type {
  CreatePlanFromIntentRequest,
  DecisionCandidateRead,
  PlanItemRead,
  PlanRead,
  PlanAdaptationRead,
  RecommendationResponse,
  SelectOptionRequest,
} from '../types/planning';

/**
 * Creates a structured plan from a free-text intention.
 * Endpoint: POST /api/v1/planning/requests
 */
export async function createPlanFromIntent(request: string): Promise<PlanRead> {
  const body: CreatePlanFromIntentRequest = { request };
  return apiClient<PlanRead>('/planning/requests', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Retrieves an existing plan by ID.
 * Endpoint: GET /api/v1/planning/plans/{plan_id}
 */
export async function getPlan(planId: string): Promise<PlanRead> {
  return apiClient<PlanRead>(`/planning/plans/${planId}`, {
    method: 'GET',
  });
}

/**
 * Retrieves recommendations tailored to the specified plan.
 * Endpoint: GET /api/v1/planning/plans/{plan_id}/recommendations
 */
export async function getPlanRecommendations(
  planId: string
): Promise<RecommendationResponse> {
  return apiClient<RecommendationResponse>(
    `/planning/plans/${planId}/recommendations`,
    { method: 'GET' }
  );
}

/**
 * Adds an authoritative recommendation candidate to the plan.
 * Endpoint: POST /api/v1/planning/plans/{plan_id}/items/from-option
 */
export async function addOptionToPlan(
  planId: string,
  candidate: DecisionCandidateRead
): Promise<PlanItemRead> {
  const body: SelectOptionRequest = {
    option_id: candidate.option_id,
    option_type: candidate.option_type,
  };

  return apiClient<PlanItemRead>(`/planning/plans/${planId}/items/from-option`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Modifies an existing plan using a conversational request while retaining context.
 * Endpoint: POST /api/v1/planning/plans/{plan_id}/modifications
 */
export async function modifyPlan(
  planId: string,
  request: string
): Promise<PlanRead> {
  return apiClient<PlanRead>(`/planning/plans/${planId}/modifications`, {
    method: 'POST',
    body: JSON.stringify({ request }),
  });
}

/**
 * Proposes a non-destructive plan adaptation with diffs.
 * Endpoint: POST /api/v1/planning/plans/{plan_id}/adapt
 */
export async function proposePlanAdaptation(
  planId: string,
  request: string
): Promise<PlanAdaptationRead> {
  return apiClient<PlanAdaptationRead>(`/planning/plans/${planId}/adapt`, {
    method: 'POST',
    body: JSON.stringify({ request }),
  });
}

/**
 * Commits an accepted plan adaptation.
 * Endpoint: POST /api/v1/planning/plans/{plan_id}/adapt/apply
 */
export async function applyPlanAdaptation(
  planId: string,
  request: string
): Promise<PlanRead> {
  return apiClient<PlanRead>(`/planning/plans/${planId}/adapt/apply`, {
    method: 'POST',
    body: JSON.stringify({ request }),
  });
}
