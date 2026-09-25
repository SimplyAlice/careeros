from __future__ import annotations

from enum import Enum


class TransportMode(str, Enum):
    WALK = "walk"
    BUS = "bus"
    TRAIN = "train"
    RIDE_HAIL = "ride_hail"
    CYCLE = "cycle"
    SHUTTLE = "shuttle"
    OTHER = "other"


class BookingCapability(str, Enum):
    NO_BOOKING = "no_booking"
    EXTERNAL_HANDOFF = "external_handoff"
    DEEPLINK = "deeplink"
    EMBEDDED = "embedded"
    API_BOOKING = "api_booking"


class MobilityLiveStatus(str, Enum):
    SCHEDULED = "scheduled"
    ESTIMATED = "estimated"
    LIVE = "live"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class MobilitySourceType(str, Enum):
    OFFICIAL_REALTIME = "official_realtime"
    OFFICIAL_TIMETABLE = "official_timetable"
    APPROVED_PROVIDER_API = "approved_provider_api"
    TRUSTED_THIRD_PARTY = "trusted_third_party"
    CROWD_REPORT = "crowd_report"
    CALCULATED = "calculated"
    UNKNOWN = "unknown"


def get_source_hierarchy_weight(source_type: MobilitySourceType) -> int:
    """Return numeric trust weight for evidence comparison. Higher is more trusted."""
    weights = {
        MobilitySourceType.OFFICIAL_REALTIME: 100,
        MobilitySourceType.OFFICIAL_TIMETABLE: 80,
        MobilitySourceType.APPROVED_PROVIDER_API: 70,
        MobilitySourceType.TRUSTED_THIRD_PARTY: 50,
        MobilitySourceType.CALCULATED: 40,
        MobilitySourceType.CROWD_REPORT: 20,
        MobilitySourceType.UNKNOWN: 0,
    }
    return weights.get(source_type, 0)
