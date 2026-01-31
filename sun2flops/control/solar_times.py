"""Solar time calculations for sunrise/sunset."""

import numpy as np
import pandas as pd
from pvlib import solarposition

from sun2flops.config import SiteConfig


def compute_sun_times(
    index: pd.DatetimeIndex,
    site: SiteConfig,
) -> pd.DataFrame:
    """
    Compute sunrise/sunset times and derived quantities for each timestep.

    Parameters
    ----------
    index : pd.DatetimeIndex
        Time index (must be timezone-aware)
    site : SiteConfig
        Site location configuration

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - seconds_to_sunrise: seconds until next sunrise (0 during day)
        - is_night: boolean indicating nighttime
        - sunrise: next sunrise timestamp
        - sunset: previous/current sunset timestamp
    """
    # Get solar position for zenith angle
    solpos = solarposition.get_solarposition(
        index,
        site.latitude,
        site.longitude,
        altitude=site.altitude_m or 0,
    )

    # Determine if it's night (sun below horizon)
    is_night = solpos['apparent_elevation'] < 0

    # Get sun rise/set times for each day in the index
    # We need to look at a range of dates that covers the index
    dates = pd.DatetimeIndex(index.date).unique()

    # Extend by one day on each side to handle edge cases
    # The date_range needs to be localized for sun_rise_set_transit_spa
    tz = index.tz if index.tz is not None else site.timezone
    date_range = pd.date_range(
        dates.min() - pd.Timedelta(days=1),
        dates.max() + pd.Timedelta(days=1),
        freq='D',
        tz=tz,
    )

    # Calculate sunrise/sunset for each date
    sun_times = solarposition.sun_rise_set_transit_spa(
        date_range,
        site.latitude,
        site.longitude,
        how='numpy',
    )

    # Build lookup of sunrise times
    # sunrise column contains the sunrise time for each day
    sunrise_times = pd.Series(sun_times['sunrise'].values, index=date_range)
    sunset_times = pd.Series(sun_times['sunset'].values, index=date_range)

    # For each timestamp, find the next sunrise
    seconds_to_sunrise = np.zeros(len(index))
    next_sunrise = pd.Series(index=index, dtype='datetime64[ns, UTC]')

    for i, ts in enumerate(index):
        ts_date = ts.date()

        # Get today's sunrise
        today_sunrise = sunrise_times.get(pd.Timestamp(ts_date))
        tomorrow_sunrise = sunrise_times.get(pd.Timestamp(ts_date) + pd.Timedelta(days=1))

        # Convert to same timezone for comparison
        if today_sunrise is not None and pd.notna(today_sunrise):
            if hasattr(ts, 'tz') and ts.tz is not None:
                today_sunrise = pd.Timestamp(today_sunrise).tz_convert(ts.tz)
            else:
                today_sunrise = pd.Timestamp(today_sunrise)

        if tomorrow_sunrise is not None and pd.notna(tomorrow_sunrise):
            if hasattr(ts, 'tz') and ts.tz is not None:
                tomorrow_sunrise = pd.Timestamp(tomorrow_sunrise).tz_convert(ts.tz)
            else:
                tomorrow_sunrise = pd.Timestamp(tomorrow_sunrise)

        # Determine next sunrise
        if today_sunrise is not None and pd.notna(today_sunrise) and ts < today_sunrise:
            next_sr = today_sunrise
        elif tomorrow_sunrise is not None and pd.notna(tomorrow_sunrise):
            next_sr = tomorrow_sunrise
        else:
            next_sr = ts + pd.Timedelta(hours=12)  # Fallback

        # Calculate seconds to sunrise
        if is_night.iloc[i]:
            delta = (next_sr - ts).total_seconds()
            seconds_to_sunrise[i] = max(0, delta)
        else:
            seconds_to_sunrise[i] = 0.0

        next_sunrise.iloc[i] = next_sr

    result = pd.DataFrame({
        'seconds_to_sunrise': seconds_to_sunrise,
        'is_night': is_night.values,
        'solar_elevation': solpos['apparent_elevation'].values,
    }, index=index)

    return result
