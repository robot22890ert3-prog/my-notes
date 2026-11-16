import asyncio
import json
import websockets

CLIENT_TOKEN = "токен_для_телефона_456"      # для подключения к серверу
AGENT_TOKEN = "мой_секретный_токен_123"      # токен, который ждёт агент


async def main():
    async with websockets.connect("ws://localhost:8000/ws/client") as ws:
        # Регистрация на сервере (токен клиента)
        await ws.send(json.dumps({"token": CLIENT_TOKEN}))
        reg = await ws.recv()
        print("Регистрация:", reg)

        # Небольшая пауза, чтобы сервер вошёл в цикл ожидания
        await asyncio.sleep(0.5)

        # Отправляем команду status с токеном АГЕНТА
        await ws.send(json.dumps({
            "token": AGENT_TOKEN,
            "action": "status",
        }))
        print("Команда отправлена, ждём ответ 5 сек...")

        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print("Ответ:", json.dumps(json.loads(resp), ensure_ascii=False, indent=2))
        except asyncio.TimeoutError:
            print("[!] Ответ не пришёл за 5 секунд")


if __name__ == "__main__":
    asyncio.run(main())