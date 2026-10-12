#!/usr/bin/env python3

"""
Validation helpers for AviationWeather.gov METAR stations.
"""

import json
import re

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATION_INFO_URL = (
    "https://aviationweather.gov/api/data/stationinfo"
)

ICAO_PATTERN = re.compile(r"^[A-Z]{4}$")


class MetarVerificationUnavailable(Exception):

    """Raised when the authoritative station source cannot be checked."""


def is_valid_icao_format(code):
    """
    Return True only for a four-letter ICAO identifier.
    """

    return bool(
        ICAO_PATTERN.fullmatch(
            str(code or "").strip().upper()
        )
    )


def find_unavailable_metar_airports(codes, timeout=10):
    """
    Return submitted ICAO codes that are not registered as METAR
    stations by AviationWeather.gov.

    Raises MetarVerificationUnavailable when the source cannot be
    checked reliably.
    """

    normalised_codes = []

    for code in codes:
        code = str(code or "").strip().upper()

        if code and code not in normalised_codes:
            normalised_codes.append(code)

    if not normalised_codes:
        return []

    query = urlencode({
        "ids": ",".join(normalised_codes),
        "format": "json",
    })

    request = Request(
        f"{STATION_INFO_URL}?{query}",
        headers={
            "User-Agent": "SvxLink-Dash-V4.1",
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            status = response.getcode()

            if status == 204:
                return normalised_codes

            if status != 200:
                raise MetarVerificationUnavailable(
                    "The METAR station source returned "
                    f"HTTP status {status}."
                )

            payload = response.read()

    except HTTPError as exc:
        if exc.code == 204:
            return normalised_codes

        raise MetarVerificationUnavailable(
            "The METAR station source returned "
            f"HTTP status {exc.code}."
        ) from exc

    except (URLError, TimeoutError, OSError) as exc:
        raise MetarVerificationUnavailable(
            "The METAR station source could not be reached."
        ) from exc

    try:
        records = json.loads(
            payload.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetarVerificationUnavailable(
            "The METAR station source returned invalid data."
        ) from exc

    if not isinstance(records, list):
        raise MetarVerificationUnavailable(
            "The METAR station source returned invalid data."
        )

    available_codes = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        station_code = str(
            record.get("icaoId")
            or record.get("id")
            or ""
        ).strip().upper()

        site_types = record.get("siteType", [])

        if (
            station_code
            and isinstance(site_types, list)
            and "METAR" in site_types
        ):
            available_codes.add(station_code)

    return [
        code
        for code in normalised_codes
        if code not in available_codes
    ]
