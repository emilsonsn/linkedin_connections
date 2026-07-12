from __future__ import annotations

import logging
import socket
import subprocess
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings


class ChromeBrowser:
    """Inicia o Chrome com perfil persistente e anexa o Selenium a ele."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver: WebDriver | None = None
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> WebDriver:
        self.settings.chromedriver_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_profile_directory()
        self._launch_chrome()
        try:
            self._wait_for_debugger()
            options = Options()
            options.binary_location = self.settings.chrome_binary
            options.debugger_address = self.settings.chrome_debugger_address
            self.driver = webdriver.Chrome(
                service=Service(log_output=self.settings.chromedriver_log_path),
                options=options,
            )
        except Exception:
            self.close()
            raise

        self.logger.info("Chrome conectado em %s", self.settings.chrome_debugger_address)
        return self.driver

    def close(self) -> None:
        try:
            if self.driver is not None:
                self.driver.quit()
        finally:
            self.driver = None
            self._stop_managed_process()

    def restart(self) -> WebDriver:
        """Encerra a sessao atual e inicia uma nova com o mesmo perfil."""
        self.logger.info("Reiniciando o Chrome")
        self.close()
        return self.start()

    def _ensure_profile_directory(self) -> None:
        self.settings.chrome_user_data_dir.mkdir(parents=True, exist_ok=True)

    def _stop_managed_process(self) -> None:
        if self.process is None or self.process.poll() is not None:
            self.process = None
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.logger.warning("Chrome nao encerrou no prazo; finalizando o processo iniciado pelo bot.")
            self.process.kill()
            self.process.wait()
        finally:
            self.process = None

    def _launch_chrome(self) -> None:
        self.logger.info("Abrindo Chrome com perfil em %s", self.settings.chrome_user_data_dir)
        self.process = subprocess.Popen(
            [
                self.settings.chrome_binary,
                f"--remote-debugging-port={self.settings.chrome_debugging_port}",
                f"--user-data-dir={self.settings.chrome_user_data_dir}",
                "--disable-dev-shm-usage",
                "--headless=new",
                "--disable-gpu",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _wait_for_debugger(self) -> None:
        host, port = self.settings.chrome_debugger_address.rsplit(":", maxsplit=1)
        for _ in range(15):
            try:
                with socket.create_connection((host, int(port)), timeout=1):
                    return
            except OSError:
                time.sleep(1)

        raise RuntimeError(
            f"O Chrome nao respondeu em {self.settings.chrome_debugger_address}."
        )
