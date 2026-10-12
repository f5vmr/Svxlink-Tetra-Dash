#!/usr/bin/env python3

import unittest

from services.version_service import (
    get_dashboard_name,
    get_dashboard_title,
    get_dashboard_version,
    get_version_info,
)


class VersionServiceTests(unittest.TestCase):

    def test_dashboard_reports_version_4_1(self):
        self.assertEqual(
            get_dashboard_version(),
            "4.1",
        )
        self.assertEqual(
            get_dashboard_name(),
            "SvxLink-Dash-V4.1",
        )
        self.assertEqual(
            get_dashboard_title(),
            "SvxLink-Dash-V4.1",
        )

        version_info = get_version_info()

        self.assertEqual(
            version_info["dashboard"],
            "4.1",
        )
        self.assertEqual(
            version_info["dashboard_name"],
            "SvxLink-Dash-V4.1",
        )
        self.assertEqual(
            version_info["dashboard_title"],
            "SvxLink-Dash-V4.1",
        )


if __name__ == "__main__":
    unittest.main()
