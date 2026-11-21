"""Public errors whose messages never contain upstream bodies or credentials."""


class BridgeError(Exception):
    """An expected, safe-to-display failure."""
