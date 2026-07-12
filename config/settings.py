"""Carregamento e validação das configurações de execução."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from config.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DAILY_CONNECTION_LIMIT,
    DEFAULT_MAX_BATCH_PAUSE_SECONDS,
    DEFAULT_MAX_BROWSER_RESTARTS_WITHOUT_SUGGESTIONS,
    DEFAULT_MAX_INVITATION_PAUSE_SECONDS,
    DEFAULT_MIN_BATCH_PAUSE_SECONDS,
    DEFAULT_MIN_INVITATION_PAUSE_SECONDS,
    DEFAULT_SCROLL_PAUSE_SECONDS,
    DEFAULT_WAIT_SECONDS,
    GOOGLE_CHROME_BINARY,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes", "sim", "s"}:
        return True
    if normalized_value in {"0", "false", "no", "nao", "não", "n"}:
        return False
    raise ValueError(f"{name} deve ser um valor booleano valido.")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um numero inteiro.") from error


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um numero.") from error


@dataclass(frozen=True, slots=True)
class Settings:
    daily_connection_limit: int
    wait_seconds: int
    scroll_pause_seconds: float
    min_invitation_pause_seconds: float
    max_invitation_pause_seconds: float
    batch_size: int
    min_batch_pause_seconds: float
    max_batch_pause_seconds: float
    max_browser_restarts_without_suggestions: int
    chrome_binary: str
    chrome_user_data_dir: Path
    chrome_debugger_address: str
    chromedriver_log_path: Path
    output_xlsx_path: Path
    log_dir: Path
    log_level: str
    dry_run: bool
    keep_browser_open: bool

    @property
    def chrome_debugging_port(self) -> int:
        _, separator, port = self.chrome_debugger_address.rpartition(":")
        if not separator:
            raise ValueError("CHROME_DEBUGGER_ADDRESS deve ter o formato host:porta.")
        try:
            parsed_port = int(port)
        except ValueError as error:
            raise ValueError("A porta de CHROME_DEBUGGER_ADDRESS deve ser numerica.") from error
        if not 1 <= parsed_port <= 65535:
            raise ValueError("A porta de CHROME_DEBUGGER_ADDRESS deve estar entre 1 e 65535.")
        return parsed_port

    @classmethod
    def load(cls) -> Settings:
        """Carrega o `.env` sem sobrescrever variáveis já definidas no ambiente."""
        load_dotenv(ENV_FILE)

        min_invitation_pause_seconds = max(
            0.0,
            _get_float("MIN_INVITATION_PAUSE_SECONDS", DEFAULT_MIN_INVITATION_PAUSE_SECONDS),
        )
        min_batch_pause_seconds = max(
            0.0,
            _get_float("MIN_BATCH_PAUSE_SECONDS", DEFAULT_MIN_BATCH_PAUSE_SECONDS),
        )
        legacy_restarts = _get_int(
            "MAX_PAGE_REFRESHES_WITHOUT_SUGGESTIONS",
            DEFAULT_MAX_BROWSER_RESTARTS_WITHOUT_SUGGESTIONS,
        )
        configuration = cls(
            daily_connection_limit=max(0, _get_int("DAILY_CONNECTION_LIMIT", DEFAULT_DAILY_CONNECTION_LIMIT)),
            wait_seconds=max(1, _get_int("WAIT_SECONDS", DEFAULT_WAIT_SECONDS)),
            scroll_pause_seconds=max(0.0, _get_float("SCROLL_PAUSE_SECONDS", DEFAULT_SCROLL_PAUSE_SECONDS)),
            min_invitation_pause_seconds=min_invitation_pause_seconds,
            max_invitation_pause_seconds=max(
                min_invitation_pause_seconds,
                _get_float("MAX_INVITATION_PAUSE_SECONDS", DEFAULT_MAX_INVITATION_PAUSE_SECONDS),
            ),
            batch_size=max(1, _get_int("BATCH_SIZE", DEFAULT_BATCH_SIZE)),
            min_batch_pause_seconds=min_batch_pause_seconds,
            max_batch_pause_seconds=max(
                min_batch_pause_seconds,
                _get_float("MAX_BATCH_PAUSE_SECONDS", DEFAULT_MAX_BATCH_PAUSE_SECONDS),
            ),
            max_browser_restarts_without_suggestions=max(
                0,
                _get_int("MAX_BROWSER_RESTARTS_WITHOUT_SUGGESTIONS", legacy_restarts),
            ),
            chrome_binary=os.getenv("CHROME_BINARY", GOOGLE_CHROME_BINARY),
            chrome_user_data_dir=Path(os.getenv("CHROME_USER_DATA_DIR", str(Path.home() / ".linkedin-selenium"))),
            chrome_debugger_address=os.getenv("CHROME_DEBUGGER_ADDRESS", "127.0.0.1:9222"),
            chromedriver_log_path=Path(os.getenv("CHROMEDRIVER_LOG_PATH", str(PROJECT_DIR / "logs" / "chromedriver.log"))),
            output_xlsx_path=Path(os.getenv("OUTPUT_XLSX_PATH", str(Path.home() / "Documentos" / "linkedin_connections.xlsx"))),
            log_dir=Path(os.getenv("LOG_DIR", str(PROJECT_DIR / "logs"))),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            dry_run=_get_bool("DRY_RUN", False),
            keep_browser_open=_get_bool("KEEP_BROWSER_OPEN", True),
        )
        _ = configuration.chrome_debugging_port
        return configuration
