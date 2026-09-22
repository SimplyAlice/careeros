class PlanningNotFoundError(Exception):
    """Raised when a user cannot access a requested planning resource."""


class PlanItemNotFoundError(Exception):
    """Raised when a user cannot access a requested plan item."""


class OptionNotFoundError(Exception):
    """Raised when a requested planning option does not exist in the source."""


class UnsupportedOptionTypeError(Exception):
    """Raised when a selection references an option type that is not supported."""
