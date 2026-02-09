from __future__ import annotations

import pandas as pd
import pvlib

from sun2flops.config.models import SiteConfig


def seconds_to_next_sunrise(index: pd.DatetimeIndex, site: SiteConfig) -> pd.Series:
    """
    Compute seconds remaining until the next sunrise for each timestamp.
    Return series aligned to index.
    """
    if index.tz is None:
        raise ValueError("index must be timezone-aware")

    location = pvlib.location.Location(
        latitude=site.latitude,
        longitude=site.longitude,
        tz=site.timezone,
        altitude=site.altitude_m,
        name=site.name,
    )

    dates = pd.DatetimeIndex(index.normalize().unique())
    dates_with_next = dates.union(dates + pd.Timedelta(days=1))
    sun_times = location.get_sun_rise_set_transit(dates_with_next)
    sunrise_map = sun_times["sunrise"].to_dict()

    seconds_to = []
    for ts in index:
        date = ts.normalize()
        sunrise = sunrise_map.get(date)
        if sunrise is None:
            seconds_to.append(float("nan"))
            continue
        if ts < sunrise:
            delta = sunrise - ts
        else:
            next_date = date + pd.Timedelta(days=1)
            sunrise_next = sunrise_map.get(next_date)
            if sunrise_next is None:
                seconds_to.append(float("nan"))
                continue
            delta = sunrise_next - ts
        seconds_to.append(delta.total_seconds())

    return pd.Series(seconds_to, index=index, name="sec_to_sunrise")
