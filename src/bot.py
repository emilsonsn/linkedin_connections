from __future__ import annotations

import logging
import random
import time
import unicodedata
from collections.abc import Callable

from selenium.webdriver.remote.webelement import WebElement

from config.constants import MAX_SCROLL_ATTEMPTS_WITHOUT_CLICK
from config.settings import Settings
from src.linkedin import LinkedInClient
from src.models import PersonInfo, RunStats
from src.storage import ConnectionWorkbook


class ConnectionBot:
    def __init__(
        self,
        linkedin: LinkedInClient,
        workbook: ConnectionWorkbook,
        restart_browser: Callable[[], LinkedInClient],
        settings: Settings,
    ) -> None:
        self.linkedin = linkedin
        self.workbook = workbook
        self.restart_browser = restart_browser
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> RunStats:
        self.linkedin.open_suggestions()
        stats = RunStats()
        browser_restarts_without_suggestions = 0
        seen_profiles: set[str] = set()
        while stats.clicked < self.settings.daily_connection_limit:
            buttons = self.linkedin.find_connect_buttons()
            candidate = self._pick_candidate(buttons, seen_profiles)

            if candidate is None:
                stats.scrolls_without_click += 1
                if stats.scrolls_without_click >= MAX_SCROLL_ATTEMPTS_WITHOUT_CLICK:
                    if (
                        browser_restarts_without_suggestions
                        < self.settings.max_browser_restarts_without_suggestions
                    ):
                        browser_restarts_without_suggestions += 1
                        self.logger.info(
                            "Sem sugestoes apos %s rolagens; reiniciando o navegador (%s/%s).",
                            stats.scrolls_without_click,
                            browser_restarts_without_suggestions,
                            self.settings.max_browser_restarts_without_suggestions,
                        )
                        self.linkedin = self.restart_browser()
                        self.linkedin.open_suggestions()
                        stats.scrolls_without_click = 0
                        seen_profiles.clear()
                        continue
                    self.logger.info("Nenhuma sugestao encontrada apos %s rolagens", stats.scrolls_without_click)
                    break
                self.linkedin.scroll_for_more_suggestions()
                continue

            stats.scrolls_without_click = 0
            button, person = candidate
            self.logger.info("Tentando conectar: %s - %s", person.name, person.description)
            clicked = self.linkedin.invite(button)
            status = "dry_run" if self.settings.dry_run else ("pendente_confirmado" if clicked else "nao_confirmado")
            self.workbook.append(person, status)
            if clicked:
                stats.clicked += 1
                action = "Perfis simulados" if self.settings.dry_run else "Convites confirmados"
                self.logger.info("%s: %s/%s", action, stats.clicked, self.settings.daily_connection_limit)
                self._wait_after_invitation(stats.clicked)
            else:
                stats.skipped += 1
        return stats

    def _pick_candidate(
        self, buttons: list[WebElement], seen_profiles: set[str]
    ) -> tuple[WebElement, PersonInfo] | None:
        for button in buttons:
            person = self.linkedin.person_info(button)
            key = person.profile_url or person.name
            if key in seen_profiles:
                continue
            seen_profiles.add(key)
            if not self._matches_filter(person):
                self.logger.info("Fora do filtro de area: %s - %s", person.name, person.description)
                continue
            return button, person
        return None

    def _matches_filter(self, person: PersonInfo) -> bool:
        if not self.settings.target_keywords:
            return True
        description = self._normalize(person.description)
        return any(self._normalize(keyword) in description for keyword in self.settings.target_keywords)

    @staticmethod
    def _normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text)
        return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()

    def _wait_after_invitation(self, invitations_sent: int) -> None:
        if self.settings.dry_run or invitations_sent >= self.settings.daily_connection_limit:
            return

        if invitations_sent % self.settings.batch_size == 0:
            seconds = random.uniform(
                self.settings.min_batch_pause_seconds,
                self.settings.max_batch_pause_seconds,
            )
            self.logger.info(
                "Lote de %s convites concluido; aguardando %.1f segundos.",
                self.settings.batch_size,
                seconds,
            )
        else:
            seconds = random.uniform(
                self.settings.min_invitation_pause_seconds,
                self.settings.max_invitation_pause_seconds,
            )
            self.logger.info("Aguardando %.1f segundos antes do proximo convite.", seconds)

        time.sleep(seconds)
