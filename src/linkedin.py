from __future__ import annotations

import logging
import time
from typing import Iterable

from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.constants import (
    CONNECT_LABEL,
    LINKEDIN_GROW_URL,
    LINKEDIN_HOME_URL,
    LINKEDIN_MY_NETWORK_URL,
    PENDING_LABEL,
)
from config.settings import Settings
from src.models import PersonInfo


class LinkedInClient:
    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def open_suggestions(self) -> None:
        self.logger.info("Abrindo LinkedIn")
        self.driver.get(LINKEDIN_HOME_URL)
        self._wait_for_page_ready()
        if "/login" in self.driver.current_url:
            raise RuntimeError(
                "Login do LinkedIn necessario. Entre manualmente no Chrome aberto e rode novamente."
            )

        self._open_my_network()
        self.logger.info("Abrindo sugestoes de conexao")
        self.driver.get(LINKEDIN_GROW_URL)
        self._wait_for_page_ready()
        time.sleep(2)
        self._scroll_workspace_for_suggestions()

    def find_connect_buttons(self) -> list[WebElement]:
        xpath = (
            "//button[not(@disabled) and "
            "(contains(normalize-space(.), 'Conectar') or contains(@aria-label, 'Conectar'))]"
            " | "
            "//a[@aria-disabled='false' and "
            "(contains(normalize-space(.), 'Conectar') or contains(@aria-label, 'Conectar'))]"
        )
        visible_buttons: list[WebElement] = []
        for button in self.driver.find_elements(By.XPATH, xpath):
            try:
                if button.is_displayed() and self._has_label(button, [CONNECT_LABEL]):
                    visible_buttons.append(button)
            except StaleElementReferenceException:
                continue
        return visible_buttons

    def scroll_for_more_suggestions(self) -> None:
        workspace = self.driver.find_element(By.CSS_SELECTOR, "main#workspace")
        self.driver.execute_script(
            "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight * 0.85));",
            workspace,
        )
        time.sleep(self.settings.scroll_pause_seconds)

    def person_info(self, button: WebElement) -> PersonInfo:
        label = self._aria_label(button) or self._visible_text(button)
        name_from_label = self._extract_person_hint(label)
        try:
            card_html, card_text = self.driver.execute_script(
                """
                const button = arguments[0]; let node = button;
                for (let depth = 0; node && depth < 10; depth += 1) {
                  const text = (node.innerText || '').trim();
                  const profileLink = node.querySelector?.('a[href*="/in/"]');
                  const paragraphs = node.querySelectorAll ? Array.from(node.querySelectorAll('p')) : [];
                  const actions = node.querySelectorAll ? Array.from(node.querySelectorAll('button,a'))
                    .filter(element => `${element.innerText || ''} ${element.getAttribute('aria-label') || ''}`.includes('Conectar')) : [];
                  if (text.includes('Conectar') && paragraphs.length >= 2 && actions.length <= 2 && (profileLink || text.length > 20)) return [node.outerHTML || '', text];
                  node = node.parentElement;
                }
                return ['', (button.innerText || button.getAttribute('aria-label') || '').trim()];
                """,
                button,
            )
        except WebDriverException:
            card_html, card_text = "", label

        person = self._parse_person(str(card_html), name_from_label)
        if person.name != "Nome nao identificado" or person.description:
            return person
        lines = self._normalize_lines(str(card_text))
        name = name_from_label or self._first_meaningful_line(lines) or person.name
        return PersonInfo(name, self._first_description_line(lines, name), person.profile_url)

    def invite(self, button: WebElement) -> bool:
        label = self._aria_label(button) or self._visible_text(button)
        person_hint = self._extract_person_hint(label)
        if self.settings.dry_run:
            self.logger.info("[dry-run] Botao encontrado: %s", label)
            return True
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", button)
            time.sleep(0.4)
            button.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", button)
        except (StaleElementReferenceException, WebDriverException) as exc:
            self.logger.warning("Pulando botao instavel: %s", exc.__class__.__name__)
            return False
        self._handle_invite_modal()
        return self._wait_until_pending(button, person_hint)

    def _open_my_network(self) -> None:
        wait = WebDriverWait(self.driver, self.settings.wait_seconds)
        try:
            self.logger.info("Clicando em Minha rede")
            menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÂÊÔÃÕÇ', 'abcdefghijklmnopqrstuvwxyzáéíóúâêôãõç'), 'minha rede') or .//*[normalize-space()='Minha rede' or normalize-space()='Minha Rede']]")))
            menu_item.click()
            self._wait_for_page_ready()
            time.sleep(2)
        except (TimeoutException, StaleElementReferenceException):
            self.logger.info("Menu Minha rede nao encontrado; abrindo URL diretamente")
            self.driver.get(LINKEDIN_MY_NETWORK_URL)
            self._wait_for_page_ready()

    def _scroll_workspace_for_suggestions(self) -> None:
        self.logger.info("Rolando pagina para carregar sugestoes de conexao")
        workspace = self.driver.find_element(By.CSS_SELECTOR, "main#workspace")
        self.driver.execute_script("arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight * 1.25));", workspace)
        time.sleep(max(self.settings.scroll_pause_seconds, 2))

    def _wait_for_page_ready(self) -> None:
        WebDriverWait(self.driver, self.settings.wait_seconds).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

    def _wait_until_pending(self, original_button: WebElement, person_hint: str) -> bool:
        def pending(_: WebDriver) -> bool:
            try:
                if self._has_label(original_button, [PENDING_LABEL]):
                    return True
            except StaleElementReferenceException:
                pass
            xpath = "//*[self::button or self::a][contains(@aria-label, 'Pendente') or contains(normalize-space(.), 'Pendente')]"
            if person_hint:
                xpath = f"//*[self::button or self::a][contains(@aria-label, 'Pendente') and contains(@aria-label, {self._xpath_literal(person_hint)})]"
            return any(element.is_displayed() for element in self.driver.find_elements(By.XPATH, xpath))
        try:
            WebDriverWait(self.driver, self.settings.wait_seconds).until(pending)
            return True
        except TimeoutException:
            self.logger.warning("Clique feito, mas nao consegui confirmar estado Pendente")
            return False

    def _handle_invite_modal(self) -> None:
        for xpath in ["//button[contains(@aria-label, 'Enviar sem nota') or normalize-space()='Enviar sem nota']", "//button[contains(@aria-label, 'Enviar') or normalize-space()='Enviar']", "//button[contains(@aria-label, 'Enviar agora') or normalize-space()='Enviar agora']", "//button[contains(@aria-label, 'Fechar') or normalize-space()='Fechar']"]:
            try:
                button = self.driver.find_element(By.XPATH, xpath)
                if button.is_displayed() and button.is_enabled():
                    button.click(); time.sleep(0.5); return
            except (NoSuchElementException, WebDriverException):
                continue

    @staticmethod
    def _visible_text(element: WebElement) -> str:
        try: return (element.text or "").strip()
        except StaleElementReferenceException: return ""

    @staticmethod
    def _aria_label(element: WebElement) -> str:
        try: return (element.get_attribute("aria-label") or "").strip()
        except StaleElementReferenceException: return ""

    def _has_label(self, element: WebElement, candidates: Iterable[str]) -> bool:
        labels = tuple(candidate.lower() for candidate in candidates)
        text, aria = self._visible_text(element).lower(), self._aria_label(element).lower()
        return any(label in text or label in aria for label in labels)

    def _parse_person(self, card_html: str, name_from_label: str) -> PersonInfo:
        if not card_html: return PersonInfo(name_from_label or "Nome nao identificado", "", "")
        soup = BeautifulSoup(card_html, "html.parser")
        profile_link = soup.find("a", href=lambda href: href and "/in/" in href)
        profile_url = profile_link.get("href", "") if profile_link else ""
        paragraphs = self._normalize_lines("\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p")))
        lines = self._normalize_lines(soup.get_text("\n", strip=True))
        name = name_from_label or self._first_meaningful_line(paragraphs) or self._first_meaningful_line(lines) or "Nome nao identificado"
        description = self._first_description_line(paragraphs, name) or self._first_description_line(lines, name)
        return PersonInfo(name, description, profile_url)

    @staticmethod
    def _normalize_lines(text: str) -> list[str]:
        ignored = {"", CONNECT_LABEL, PENDING_LABEL, "Seguir", "Enviar mensagem", "Mensagem", "Mais"}
        lines: list[str] = []
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split()).replace(" Verificado", "").strip()
            if line not in ignored and line not in lines: lines.append(line)
        return lines

    @staticmethod
    def _is_noise_line(line: str, name: str = "") -> bool:
        lowered, normalized_name = line.lower(), name.strip().lower()
        if not line or (normalized_name and (lowered == normalized_name or lowered.startswith(f"{normalized_name},") or lowered.startswith(f"{normalized_name} "))): return True
        if normalized_name and normalized_name in lowered and ("premium" in lowered or "verificado" in lowered or "verified" in lowered): return True
        if lowered.startswith(("conectar", "pendente", "seguir", "patrocinado")) or lowered in {"premium", "verificado", "verified", "1º", "2º", "3º", "1°", "2°", "3°"}: return True
        return "conex" in lowered and any(word in lowered for word in ("em comum", "mútua", "mutua", "conexão", "conexões", "conexao", "conexoes"))

    def _first_meaningful_line(self, lines: list[str]) -> str:
        return next((line for line in lines if not self._is_noise_line(line)), "")

    def _first_description_line(self, lines: list[str], name: str) -> str:
        return next((line for line in lines if not self._is_noise_line(line, name)), "")

    @staticmethod
    def _extract_person_hint(label: str) -> str:
        cleaned = label.strip()
        for prefix in ("Convidar ", "Conectar-se a ", "Conectar com ", "Conectar a ", "Conectar "):
            if cleaned.startswith(prefix): cleaned = cleaned.removeprefix(prefix).strip(); break
        for suffix in (" para se conectar", " para conectar"):
            if cleaned.endswith(suffix): return cleaned.removesuffix(suffix).strip()
        return cleaned if cleaned != label.strip() else ""

    @staticmethod
    def _xpath_literal(value: str) -> str:
        if "'" not in value: return f"'{value}'"
        if '"' not in value: return f'"{value}"'
        return "concat(" + ', "\'", '.join(f"'{part}'" for part in value.split("'")) + ")"
