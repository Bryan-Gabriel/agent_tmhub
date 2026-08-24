from models.models import HK, VPN
from dotenv import load_dotenv
from getmac import get_mac_address
from os import getenv
import socketio
import asyncio

load_dotenv()
API_URL = getenv("API_URL")
AGENT_ID = get_mac_address()
sio = socketio.AsyncClient()

@sio.event
async def connect(): print(f"Conectado! MAC: {AGENT_ID}"); await sio.emit("register", {"agent_id": AGENT_ID})

@sio.event
async def disconnect(): print("Desconectado!")

@sio.on("command")
async def on_command(command):
    if not isinstance(command, dict):
        print(f"Formato inválido recebido: {type(command).__name__}")
        return

    match command.get("type"):
        case "HK_adjust":
            adjusts = command.get("data", [])
            hk = HK(command.get("isOpen", False))
            hk.set_adjust(adjusts, open_tab_moviment=True)

        case _: print(f"Tipo de comando desconhecido: {command.get('type')}")

async def main():
    print(f"Agente iniciado - MAC: {AGENT_ID}")
    while True:
        try:
            await sio.connect(API_URL)
            await sio.wait()
        except Exception as e:
            print(f"Conexão perdida: {e}, reconectando em 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__": asyncio.run(main())