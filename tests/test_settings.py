from __future__ import annotations

import unittest
from pathlib import Path

from config.settings import Settings


def make_settings(address: str = "127.0.0.1:9222") -> Settings:
    return Settings(
        daily_connection_limit=10,
        wait_seconds=15,
        scroll_pause_seconds=1.0,
        min_invitation_pause_seconds=3.0,
        max_invitation_pause_seconds=8.0,
        batch_size=10,
        min_batch_pause_seconds=30.0,
        max_batch_pause_seconds=60.0,
        max_browser_restarts_without_suggestions=1,
        chrome_binary="google-chrome",
        chrome_user_data_dir=Path("/tmp/profile"),
        chrome_debugger_address=address,
        chromedriver_log_path=Path("/tmp/chromedriver.log"),
        output_xlsx_path=Path("/tmp/connections.xlsx"),
        log_dir=Path("/tmp/logs"),
        log_level="INFO",
        dry_run=False,
        keep_browser_open=False,
    )


class SettingsTest(unittest.TestCase):
    def test_extracts_debugging_port(self) -> None:
        self.assertEqual(make_settings("localhost:9333").chrome_debugging_port, 9333)

    def test_rejects_invalid_debugging_address(self) -> None:
        with self.assertRaises(ValueError):
            _ = make_settings("localhost").chrome_debugging_port
