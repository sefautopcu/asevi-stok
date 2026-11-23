"""Timezone-aware date and time formatting helpers."""
import datetime
import zoneinfo


def simdi_tr_str(format_str="%Y-%m-%d %H:%M", simdi_fn=None):
    """Format current Turkey time, falling back to local time if zone data fails."""
    if simdi_fn is None:
        simdi_fn = datetime.datetime.now
    try:
        return simdi_fn(zoneinfo.ZoneInfo("Europe/Istanbul")).strftime(format_str)
    except Exception:
        return simdi_fn().strftime(format_str)
