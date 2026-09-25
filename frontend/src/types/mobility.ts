export type TransportMode =
  | 'walk'
  | 'bus'
  | 'train'
  | 'ride_hail'
  | 'cycle'
  | 'shuttle'
  | 'other';

export type BookingCapability =
  | 'no_booking'
  | 'external_handoff'
  | 'deeplink'
  | 'embedded'
  | 'api_booking';

export type MobilityLiveStatus =
  | 'scheduled'
  | 'estimated'
  | 'live'
  | 'delayed'
  | 'cancelled'
  | 'unknown';

export type MobilitySourceType =
  | 'official_realtime'
  | 'official_timetable'
  | 'approved_provider_api'
  | 'trusted_third_party'
  | 'crowd_report'
  | 'calculated'
  | 'unknown';

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface MobilityEvidenceRead {
  claim: string;
  source: string;
  source_type: MobilitySourceType;
  observed_at: string;
  retrieved_at: string;
  expires_at?: string | null;
  confidence: number;
  relevant_provider: string;
  relevant_route_or_stop?: string | null;
}

export interface MobilityOptionRead {
  id: string;
  provider_id: string;
  provider_name: string;
  mode: TransportMode;
  origin: string;
  destination: string;
  departure_time?: string | null;
  arrival_time?: string | null;
  duration_minutes?: number | null;
  cost?: number | string | null;
  cost_is_unknown: boolean;
  currency: string;
  walking_duration_minutes?: number | null;
  transfers: number;
  availability: string;
  live_status: MobilityLiveStatus;
  booking_capability: BookingCapability;
  booking_url?: string | null;
  source: string;
  source_type: MobilitySourceType;
  retrieved_at: string;
  confidence: number;
  summary: string;
  evidence: MobilityEvidenceRead[];
}

export interface MobilityOptionsResponse {
  options: MobilityOptionRead[];
  retrieved_at: string;
  total_options: number;
  query_summary: string;
}

export interface MobilityRequirementRequest {
  origin: string;
  destination: string;
  departure_time?: string | null;
  arrival_time?: string | null;
  date?: string | null;
  party_size?: number;
  preferred_modes?: TransportMode[];
  excluded_modes?: TransportMode[];
  max_walking_minutes?: number | null;
  origin_coordinates?: Coordinates | null;
  destination_coordinates?: Coordinates | null;
}

export interface ProviderCapabilityRead {
  provider_id: string;
  name: string;
  supported_modes: TransportMode[];
  has_route_data: boolean;
  has_timetable: boolean;
  has_realtime: boolean;
  has_service_alerts: boolean;
  has_fare_estimates: boolean;
  booking_capability: BookingCapability;
  api_available: boolean;
  auth_required: boolean;
  official_source_url?: string | null;
  is_enabled: boolean;
  notes: string;
}
