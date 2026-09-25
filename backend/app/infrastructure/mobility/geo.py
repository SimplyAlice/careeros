from __future__ import annotations

import math
import re

# Reference Cape Town geographic locations (latitude, longitude)
CAPE_TOWN_LOCATIONS: dict[str, tuple[float, float]] = {
    "civic centre": (-33.9189, 18.4233),
    "cape town cbd": (-33.9249, 18.4241),
    "city bowl": (-33.9249, 18.4241),
    "cape town station": (-33.9219, 18.4247),
    "v&a waterfront": (-33.9036, 18.4205),
    "waterfront": (-33.9036, 18.4205),
    "gardens": (-33.9350, 18.4100),
    "kloof street": (-33.9300, 18.4110),
    "tamboerskloof": (-33.9280, 18.4050),
    "sea point": (-33.9180, 18.3880),
    "green point": (-33.9070, 18.4060),
    "camps bay": (-33.9510, 18.3780),
    "clifton": (-33.9380, 18.3750),
    "hout bay": (-34.0450, 18.3580),
    "woodstock": (-33.9300, 18.4480),
    "salt river": (-33.9330, 18.4610),
    "observatory": (-33.9370, 18.4720),
    "mowbray": (-33.9480, 18.4730),
    "rosebank": (-33.9570, 18.4780),
    "rondebosch": (-33.9630, 18.4830),
    "newlands": (-33.9740, 18.4590),
    "claremont": (-33.9810, 18.4660),
    "wynberg": (-34.0040, 18.4660),
    "kalk bay": (-34.1270, 18.4480),
    "muizenberg": (-34.1080, 18.4710),
    "fish hoek": (-34.1350, 18.4320),
    "simon's town": (-34.1930, 18.4320),
    "simons town": (-34.1930, 18.4320),
    "table view": (-33.8240, 18.4910),
    "dunoon": (-33.8050, 18.5370),
    "bellville": (-33.8940, 18.6290),
    "cape town international airport": (-33.9715, 18.6021),
    "airport": (-33.9715, 18.6021),
}


def find_coordinates(location_name: str) -> tuple[float, float] | None:
    """Resolve known coordinates for a Cape Town location name."""
    clean = location_name.strip().lower()
    # Direct match
    if clean in CAPE_TOWN_LOCATIONS:
        return CAPE_TOWN_LOCATIONS[clean]
    # Substring match
    for name, coords in CAPE_TOWN_LOCATIONS.items():
        if name in clean or clean in name:
            return coords
    return None


def haversine_distance_km(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    radius_earth_km = 6371.0

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_earth_km * c


def estimate_network_distance_km(
    origin: str,
    destination: str,
    origin_coords: tuple[float, float] | None = None,
    destination_coords: tuple[float, float] | None = None,
) -> float:
    """Estimate ground street distance between origin and destination in km."""
    coords1 = origin_coords or find_coordinates(origin)
    coords2 = destination_coords or find_coordinates(destination)

    if coords1 and coords2:
        direct_km = haversine_distance_km(coords1, coords2)
        # Urban circuity factor: real road networks are ~1.25 to 1.35x crow-flies distance
        return max(0.5, round(direct_km * 1.3, 1))

    # Fallback heuristic if unknown: conservative default 5.0 km
    return 5.0
