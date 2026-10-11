"""Resolve devices within their owning config entry on current and older Core."""
from .const import DOMAIN


def device_for_entry(registry, device_id: str, entry_id: str):
    """A miss in the current API must not fall back to an ambiguous lookup."""
    if hasattr(registry, "async_get_device_by_identifier"):
        return registry.async_get_device_by_identifier((DOMAIN, device_id), entry_id)
    return registry.async_get_device(identifiers={(DOMAIN, device_id)})
