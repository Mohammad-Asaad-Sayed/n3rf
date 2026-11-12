class NodeError(Exception):
    """A user-correctable node or workflow error."""


class ConflictError(Exception):
    """Raised when a save targets a stale workflow version."""
