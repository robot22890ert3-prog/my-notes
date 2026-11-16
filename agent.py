import asyncio
import json
import subprocess
import os
import io
import base64
from datetime import datetime

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ===== НАСТРОЙКИ =====
TOKEN = "мой_секретный_токен_123"      # тот же, что в server.py (AGENT_TOKEN)
AGENT_ID = "pc-1"                       # имя этого ПК в системе
# =====================


def do_lock():
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return {"status": "ok", "result": "ПК заблокирован"}


def do_shutdown():
    subprocess.run("shutdown /s /t 10", shell=True)
    return {"status": "ok", "result": "Выключение через 10 сек. Отмена: shutdown /a"}


def do_screenshot():
    if not HAS_PIL:
        return {"status": "error", "msg": "Pillow не установлен"}
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"status": "ok", "result": b64, "format": "png"}


def do_status():
    return {
        "status": "ok",
        "result": {
            "hostname": os.environ.get("COMPUTERNAME", "?"),
            "user": os.environ.get("USERNAME", "?"),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cwd": os.getcwd(),
        }
    }


def do_cmd(command: str):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding="cp866", timeout=30
        )
        return {
            "status": "ok",
            "result": {
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "code": result.returncode,
            }
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "msg": "Таймаут 30 сек"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


COMMANDS = {
    "lock": lambda _: do_lock(),
    "shutdown": lambda _: do_shutdown(),
    "screenshot": lambda _: do_screenshot(),
    "status": lambda _: do_status(),
    "cmd": lambda args: do_cmd(args.get("command", "")),
}


async def handle_message(raw: str) -> dict:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "msg": "не JSON"}

    if msg.get("token") != TOKEN:
        return {"status": "error", "msg": "неверный токен"}

    action = msg.get("action")
    if action not in COMMANDS:
        return {"status": "error", "msg": f"неизвестная команда: {action}"}

    return COMMANDS[action](msg)


# ===== Режим 1: локальный тест =====
def local_test():
    print("=" * 50)
    print("ЛОКАЛЬНЫЙ ТЕСТ АГЕНТА")
    print("Команды: lock, shutdown, screenshot, status, cmd <текст>")
    print("Выход: exit")
    print("=" * 50)

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line == "exit":
            break

        parts = line.split(maxsplit=1)
        action = parts[0]
        args = {}
        if action == "cmd" and len(parts) > 1:
            args["command"] = parts[1]

        msg = {"token": TOKEN, "action": action, **args}
        result = asyncio.run(handle_message(json.dumps(msg)))

        if action == "screenshot" and result.get("status") == "ok":
            data = base64.b64decode(result["result"])
            with open("screenshot.png", "wb") as f:
                f.write(data)
            print(f"[OK] Скриншот сохранён: screenshot.png ({len(data)} байт)")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))


# ===== Режим 2: подключение к серверу =====
async def run_agent(server_url: str):
    import websockets

    while True:
        try:
            async with websockets.connect(server_url) as ws:
                # Регистрация на сервере
                await ws.send(json.dumps({
                    "token": TOKEN,
                    "agent_id": AGENT_ID,
                }))
                resp = json.loads(await ws.recv())
                if resp.get("status") != "ok":
                    print(f"[!] Сервер отказал: {resp}")
                    return
                print(f"[+] Подключён к серверу как {resp.get('agent_id')}")

                # Слушаем команды от сервера
                async for raw in ws:
                    result = await handle_message(raw)
                    await ws.send(json.dumps(result))

        except Exception as e:
            print(f"[!] Соединение потеряно: {e}. Переподключение через 5 сек...")
            await asyncio.sleep(5)


# ===== Точка входа =====
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "connect":
        url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:8000/ws/agent"
        print(f"Подключение к {url} ...")
        try:
            asyncio.run(run_agent(url))
        except KeyboardInterrupt:
            print("\nОстановлено пользователем.")
    else:
        local_test()