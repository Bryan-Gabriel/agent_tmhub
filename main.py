import asyncio
from os import getenv

from dotenv import load_dotenv
from getmac import get_mac_address
import socketio

from models.models import HK, VPN
from models.pontomais import PontoMaisReports


load_dotenv()
API_URL = getenv("API_URL")
AGENT_ID = get_mac_address()
sio = socketio.AsyncClient()


async def _emit_pontomais_progress(command, progress, step, status="running"):
    await sio.emit("command_progress", {
        "command_id": command.get("command_id"),
        "agent_id": AGENT_ID,
        "progress": progress,
        "step": step,
        "status": status,
    })


async def _run_pontomais_jornadas(command):
    """Executa a automação web sem bloquear o recebimento de comandos."""
    loop = asyncio.get_running_loop()
    updates = asyncio.Queue()

    def report_progress(progress, step):
        loop.call_soon_threadsafe(updates.put_nowait, (progress, step))

    worker = PontoMaisReports(command["reference_date"], command["import_token"], report_progress)
    task = asyncio.create_task(asyncio.to_thread(worker.run_jornadas, API_URL))
    while not task.done():
        try:
            progress, step = await asyncio.wait_for(updates.get(), timeout=.4)
            await _emit_pontomais_progress(command, progress, step)
        except asyncio.TimeoutError:
            pass
    result = await task

    await asyncio.sleep(0)
    while not updates.empty():
        progress, step = updates.get_nowait()
        await _emit_pontomais_progress(command, progress, step)
    return result


@sio.event
async def connect():
    # agent_id é o contrato legado; os campos adicionais permitem que o
    # RPA Center reconheça este mesmo agente como compatível com Ponto Mais.
    await sio.emit("register", {
        "agent_id": AGENT_ID,
        "category": "Ponto Mais",
        "capabilities": ["HK_adjust", "pontomais_report_import"],
    })


async def _handle_hk_adjust(command):
    """Fluxo HK preservado como estava no agente original."""
    adjusts = command.get("data", [])
    hk = HK(command.get("isOpen", False))
    hk.set_adjust(adjusts, open_tab_moviment=True)


async def _handle_pontomais_report(command):
    """Módulo novo, pronto para receber outros relatórios do Ponto Mais."""
    if command.get("report") != "jornadas":
        return
    try:
        await _emit_pontomais_progress(command, 5, "Preparando agente Ponto Mais")
        await _run_pontomais_jornadas(command)
        await _emit_pontomais_progress(command, 100, "Importação concluída", status="completed")
        await sio.emit("command_done", {
            "command_id": command.get("command_id"),
            "agent_id": AGENT_ID,
            "progress": 100,
            "step": "Importação concluída",
            "status": "completed",
        })
    except Exception as error:
        await sio.emit("command_done", {
            "command_id": command.get("command_id"),
            "agent_id": AGENT_ID,
            "progress": 0,
            "step": str(error)[:180],
            "status": "failed",
        })


# Novos módulos entram aqui sem alterar os existentes.
COMMAND_HANDLERS = {
    "HK_adjust": _handle_hk_adjust,
    "pontomais_report_import": _handle_pontomais_report,
}


@sio.on("command")
async def on_command(command):
    if isinstance(command, dict) and (handler := COMMAND_HANDLERS.get(command.get("type"))):
        await handler(command)


async def main():
    while True:
        try:
            await sio.connect(API_URL)
            await sio.wait()
        except Exception:
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
