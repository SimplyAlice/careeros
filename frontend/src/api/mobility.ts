import { apiClient } from './client';
import type {
  MobilityOptionsResponse,
  MobilityRequirementRequest,
  ProviderCapabilityRead,
} from '../types/mobility';

/**
 * Evaluates transport possibilities across all active providers for a journey.
 * Endpoint: POST /api/v1/mobility/options
 */
export async function getMobilityOptions(
  request: MobilityRequirementRequest
): Promise<MobilityOptionsResponse> {
  return apiClient<MobilityOptionsResponse>('/mobility/options', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Retrieves registered mobility providers and their declared capabilities.
 * Endpoint: GET /api/v1/mobility/providers
 */
export async function getMobilityProviders(): Promise<ProviderCapabilityRead[]> {
  return apiClient<ProviderCapabilityRead[]>('/mobility/providers');
}
