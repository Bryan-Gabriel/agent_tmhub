"""Automação web dos relatórios Ponto Mais."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from os import getenv
from pathlib import Path
import re
import shutil
import tempfile
from threading import Event, Thread

import requests
from playwright.sync_api import sync_playwright

PONTOMAIS_URL = "https://app2.pontomais.com.br"
MAX_REPORT_SIZE = 30 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 180
ACTION_DELAY_MS = 4_000
PAGE_TRANSITION_DELAY_MS = 10_000


def _headless_mode():
    return str(getenv("PONTOMAIS_HEADLESS") or "true").strip().lower() not in {"0", "false", "no"}


def ponto_mais_credentials():
    login = (getenv("PONTOMAIS_LOGIN") or "").strip()
    password = getenv("PONTOMAIS_PASSWORD") or ""
    if not login or not password:
        raise RuntimeError("Defina PONTOMAIS_LOGIN e PONTOMAIS_PASSWORD no arquivo .env do agente.")
    return login, password

class PontoMaisReports:
    def __init__(self, reference_date, import_token, progress):
        self.reference_date = datetime.strptime(str(reference_date), "%Y-%m-%d").date()
        self.import_token = import_token
        self.progress = progress

    @contextmanager
    def _progressing(self, start, ceiling, step, interval_seconds=1):
        self.progress(start, step)
        stop, current, limit = Event(), start, max(start, ceiling - 1)

        def heartbeat():
            nonlocal current
            while not stop.wait(interval_seconds):
                if current < limit:
                    current += 1
                    self.progress(current, step)

        worker = Thread(target=heartbeat, name="pontomais-progress", daemon=True)
        worker.start()
        try:
            yield
        except BaseException:
            stop.set()
            worker.join(timeout=1)
            raise
        else:
            stop.set()
            worker.join(timeout=1)
            self.progress(ceiling, step)

    def _select_option(self, page, select, option):
        container = select.locator("xpath=ancestor::ng-select[1]")
        select.wait_for(state="visible", timeout=REQUEST_TIMEOUT_SECONDS * 1000)
        select.click(force=True)
        page.wait_for_timeout(ACTION_DELAY_MS)
        search = page.locator(".ng-dropdown-panel input").first
        if search.count() and search.is_visible():
            search.fill(option)
        page.locator(".ng-dropdown-panel .ng-option", has_text=re.compile(f"^{re.escape(option)}$", re.I)).first.click()
        page.wait_for_timeout(ACTION_DELAY_MS)
        selected_value = container.locator(".ng-value-label").inner_text()
        if option.casefold() not in selected_value.casefold():
            raise RuntimeError(f"O Ponto Mais não confirmou a seleção de '{option}'. O download foi interrompido.")

    def _download_jornadas(self, login, password):
        date_label = self.reference_date.strftime("%d/%m/%Y")
        self.progress(12, "Abrindo o Ponto Mais")
        with sync_playwright() as runtime:
            headless = _headless_mode()
            browser = runtime.chromium.launch(headless=headless)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                with self._progressing(13, 23, "Carregando tela de login", 1):
                    page.goto(PONTOMAIS_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(ACTION_DELAY_MS)
                self.progress(24, "Autenticando no Ponto Mais")
                login_field = page.locator("input[data-testid='login-input']:visible").first
                password_field = page.locator("input[type='password']:visible").first
                with self._progressing(25, 33, "Preenchendo credenciais", 1.2):
                    login_field.wait_for(state="visible", timeout=REQUEST_TIMEOUT_SECONDS * 1000)
                    login_field.fill(login)
                    page.wait_for_timeout(ACTION_DELAY_MS)
                    password_field.fill(password)
                    page.wait_for_timeout(ACTION_DELAY_MS)
                    page.get_by_role("button", name="Entrar", exact=True).click()
                with self._progressing(34, 41, "Validando acesso ao Ponto Mais", 1.6):
                    page.wait_for_timeout(PAGE_TRANSITION_DELAY_MS)
                if "/login" in page.url:
                    raise RuntimeError("O Ponto Mais permaneceu na tela de login; verifique as credenciais ou a validação da conta.")
                with self._progressing(42, 47, "Abrindo relatórios", 2.4):
                    page.goto(f"{PONTOMAIS_URL}/relatorios", wait_until="domcontentloaded")
                    page.wait_for_timeout(PAGE_TRANSITION_DELAY_MS)
                with self._progressing(48, 53, "Selecionando Auditoria", 1.9):
                    self._select_option(
                        page,
                        page.locator("ng-select").first.locator(".ng-input"),
                        "Auditoria",
                    )
                self.progress(54, "Definindo período do relatório")
                period = page.get_by_placeholder("Selecionar período")
                period.fill(f"{date_label} - {date_label}")
                period.press("Tab")
                with self._progressing(55, 63, "Selecionando modelo Jornadas", 1.1):
                    self._select_option(
                        page,
                        # Após escolher Auditoria, o quarto ng-select é o campo Modelo.
                        # Os anteriores são Tipo, Agrupar por e Filtrar por. Usar sua posição
                        # evita que um rótulo visual apontado pelo Angular selecione "Filtrar por".
                        page.locator("ng-select").nth(3).locator(".ng-input"),
                        "Jornadas",
                    )
                with self._progressing(64, 67, "Preparando download XLS", 1):
                    page.get_by_role("button", name=re.compile("^Baixar", re.I)).click()
                with self._progressing(68, 80, "Baixando relatório XLS", 5):
                    with page.expect_download(timeout=REQUEST_TIMEOUT_SECONDS * 1000) as pending:
                        page.locator("#relatorios-baixar-xls").click(force=True)
                with tempfile.TemporaryDirectory(prefix="tmhub-pontomais-") as directory:
                    report = Path(directory) / "jornadas.xlsx"
                    with self._progressing(80, 81, "Finalizando download", 2):
                        pending.value.save_as(report)
                        page.wait_for_timeout(5_000)
                    if not report.is_file() or report.stat().st_size > MAX_REPORT_SIZE:
                        raise RuntimeError("O relatório baixado não é válido ou excede 30 MB.")
                    yield report
            finally:
                context.close()
                browser.close()

    def run_jornadas(self, api_url):
        login, password = ponto_mais_credentials()
        try:
            for report in self._download_jornadas(login, password):
                self.progress(82, "Importando XLSX no TMHub")
                with report.open("rb") as stream:
                    with self._progressing(83, 98, "Importando XLSX no TMHub", 1.3):
                        response = requests.post(
                            f"{api_url.rstrip('/')}/jornadas/importar",
                            headers={"Access-Token": self.import_token},
                            data={"data_referencia": self.reference_date.isoformat()},
                            files={"file": ("jornadas.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                            timeout=REQUEST_TIMEOUT_SECONDS,
                            allow_redirects=False,
                        )
                if not response.ok:
                    diagnostics = Path.cwd() / "diagnosticos"
                    diagnostics.mkdir(exist_ok=True)
                    shutil.copy2(report, diagnostics / f"jornadas-{self.reference_date.isoformat()}.xlsx")
                    raise RuntimeError(f"A API recusou a importação (HTTP {response.status_code}).")
                self.progress(100, "Importação concluída")
                return response.json()
        finally:
            login = password = None
            self.import_token = None
