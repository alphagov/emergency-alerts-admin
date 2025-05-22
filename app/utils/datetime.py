from datetime import datetime


def fromisoformat_allow_z_tz(in_datetime: str):
    """
    Until Python 3.11, fromisoformat ...doesn't support ISO properly.
    Where we're currently using 3.9, we need to hack an ISO string to not end in Z so it can be parsed.
    """
    datetime_str = in_datetime
    if in_datetime.endswith("Z"):
        datetime_str = in_datetime[:-1] + "+00:00"

    return datetime.fromisoformat(datetime_str)
