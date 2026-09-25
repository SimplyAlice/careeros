from app.application.mobility.registry import MobilityProviderRegistry
from app.infrastructure.mobility.providers.bolt_provider import BoltProvider
from app.infrastructure.mobility.providers.golden_arrow_provider import GoldenArrowProvider
from app.infrastructure.mobility.providers.indrive_provider import InDriveProvider
from app.infrastructure.mobility.providers.myciti_provider import MyCiTiProvider
from app.infrastructure.mobility.providers.prasa_provider import PrasaProvider
from app.infrastructure.mobility.providers.uber_provider import UberProvider
from app.infrastructure.mobility.providers.walking_provider import WalkingProvider

__all__ = [
    "BoltProvider",
    "GoldenArrowProvider",
    "InDriveProvider",
    "MyCiTiProvider",
    "PrasaProvider",
    "UberProvider",
    "WalkingProvider",
    "create_default_mobility_registry",
]


def create_default_mobility_registry() -> MobilityProviderRegistry:
    """Instantiate and register all verified transport provider adapters."""
    registry = MobilityProviderRegistry()
    registry.register(WalkingProvider())
    registry.register(MyCiTiProvider())
    registry.register(PrasaProvider())
    registry.register(GoldenArrowProvider())
    registry.register(UberProvider())
    registry.register(BoltProvider())
    registry.register(InDriveProvider())
    return registry
