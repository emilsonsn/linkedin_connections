from __future__ import annotations

import logging
from selenium.common.exceptions import WebDriverException

from config.settings import Settings
from src.bot import ConnectionBot
from src.browser import ChromeBrowser
from src.linkedin import LinkedInClient
from src.logging_config import configure_logging
from src.storage import ConnectionWorkbook


def main() -> int:
    try:
        settings = Settings.load()
    except ValueError as error:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("main").error("Configuracao invalida: %s", error)
        return 1

    log_path = configure_logging(settings.log_dir, settings.log_level)
    logger = logging.getLogger("main")
    logger.info("Inicio da execucao. Log: %s", log_path)
    browser = ChromeBrowser(settings)

    try:
        driver = browser.start()
        bot = ConnectionBot(
            LinkedInClient(driver, settings),
            ConnectionWorkbook(settings.output_xlsx_path),
            lambda: LinkedInClient(browser.restart(), settings),
            settings,
        )
        stats = bot.run()
        action = "perfil(is) simulado(s)" if settings.dry_run else "convite(s) enviado(s)"
        logger.info("Finalizado: %s %s, %s botao(oes) pulado(s).", stats.clicked, action, stats.skipped)
        return 0
    except (RuntimeError, WebDriverException):
        logger.exception("Falha durante a execucao do bot")
        return 1
    finally:
        if not settings.keep_browser_open:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
