import asyncio
import json
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# ===== НАСТРОЙКИ =====
AGENT_TOKEN = "мой_секретный_токен_123"   # тот же, что в agent.py
CLIENT_TOKEN = "токен_для_телефона_456"    # для веб-клиента
# =====================

agents: dict[str, WebSocket] = {}
clients: dict[str, WebSocket] = {}


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Remote PC</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    margin: 0; padding: 16px;
    background: #0f172a; color: #e2e8f0;
  }
  h1 { font-size: 20px; margin: 0 0 12px; }
  .status {
    padding: 8px 12px; border-radius: 8px; margin-bottom: 12px;
    background: #1e293b; font-size: 14px;
  }
  .status.ok { background: #14532d; color: #bbf7d0; }
  .status.err { background: #7f1d1d; color: #fecaca; }
  .grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px; margin-bottom: 12px;
  }
  button {
    padding: 14px 10px; border: none; border-radius: 10px;
    font-size: 15px; font-weight: 600; color: #fff;
    background: #334155; cursor: pointer;
    transition: transform .05s, background .15s;
  }
  button:active { transform: scale(0.97); }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  .b-status { background: #2563eb; }
  .b-lock   { background: #d97706; }
  .b-shot   { background: #7c3aed; }
  .b-shut   { background: #dc2626; }
  .log {
    background: #020617; border-radius: 10px; padding: 10px;
    font-family: ui-monospace, Consolas, monospace;
    font-size: 12px; height: 220px; overflow-y: auto;
    white-space: pre-wrap; word-break: break-all;
  }
  .log div { margin-bottom: 4px; }
  .log .in  { color: #38bdf8; }
  .log .out { color: #4ade80; }
  .log .err { color: #f87171; }
  img.shot { width: 100%; border-radius: 10px; margin-top: 10px; }
</style>
</head>
<body>
  <h1>Управление ПК</h1>
  <div id="status" class="status">Подключение...</div>

  <div class="grid">
    <button class="b-status" onclick="send('status')">Статус ПК</button>
    <button class="b-lock"   onclick="send('lock')">Заблокировать</button>
    <button class="b-shot"   onclick="send('screenshot')">Скриншот</button>
    <button class="b-shut"   onclick="send('shutdown')">Выключить</button>
  </div>

  <div id="log" class="log"></div>
  <img id="shot" class="shot" style="display:none">

<script>
const TOKEN = "токен_для_телефона_456";     // для регистрации
const AGENT_TOKEN = "мой_секретный_токен_123"; // для команд агенту
const statusEl = document.getElementById('status');
const logEl = document.getElementById('log');
const shotEl = document.getElementById('shot');

let ws;
let connected = false;

function log(text, cls) {
  const d = document.createElement('div');
  d.className = cls || '';
  d.textContent = text;
  logEl.appendChild(d);
  logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(text, ok) {
  statusEl.textContent = text;
  statusEl.className = 'status ' + (ok ? 'ok' : 'err');
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/client`);

  ws.onopen = () => {
    log('Соединение открыто', 'in');
    ws.send(JSON.stringify({ token: TOKEN }));
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }

    if (msg.client_id) {
      connected = true;
      setStatus('Подключено к серверу', true);
      log('Клиент ID: ' + msg.client_id, 'out');
      if (msg.agents && msg.agents.length === 0) {
        log('Внимание: агент не подключён!', 'err');
      } else {
        log('Агенты: ' + (msg.agents || []).join(', '), 'out');
      }
      return;
    }

    if (msg.status === 'ok') {
      if (msg.result && typeof msg.result === 'object' && msg.result.hostname) {
        log('ПК: ' + msg.result.hostname + ' | юзер: ' + msg.result.user +
            ' | ' + msg.result.time, 'out');
      } else if (msg.format === 'png' && msg.result) {
        shotEl.src = 'data:image/png;base64,' + msg.result;
        shotEl.style.display = 'block';
        log('Скриншот получен', 'out');
      } else {
        log('OK: ' + JSON.stringify(msg.result), 'out');
      }
    } else if (msg.status === 'error') {
      log('Ошибка: ' + msg.msg, 'err');
    }
  };

  ws.onclose = () => {
    connected = false;
    setStatus('Отключено. Переподключение через 3 сек...', false);
    log('Соединение закрыто', 'err');
    setTimeout(connect, 3000);
  };

  ws.onerror = () => log('Ошибка WebSocket', 'err');
}

function send(action) {
  if (!ws || ws.readyState !== 1) {
    log('Нет соединения', 'err');
    return;
  }
  log('→ ' + action, 'in');
  ws.send(JSON.stringify({ token: AGENT_TOKEN, action: action }));
}

connect();
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)


@app.websocket("/ws/agent")
async def agent_endpoint(ws: WebSocket):
    await ws.accept()
    agent_id = None
    try:
        raw = await ws.receive_text()
        msg = json.loads(raw)
        if msg.get("token") != AGENT_TOKEN:
            await ws.send_text(json.dumps({"status": "error", "msg": "неверный токен агента"}))
            await ws.close()
            return

        agent_id = msg.get("agent_id") or str(uuid.uuid4())[:8]
        agents[agent_id] = ws
        print(f"[+] Агент подключён: {agent_id}")
        await ws.send_text(json.dumps({"status": "ok", "agent_id": agent_id}))

        while True:
            raw = await ws.receive_text()
            print(f"[agent {agent_id}] {raw[:200]}")
            for cid, cws in list(clients.items()):
                try:
                    await cws.send_text(raw)
                except Exception:
                    clients.pop(cid, None)

    except WebSocketDisconnect:
        print(f"[-] Агент отключён: {agent_id}")
    finally:
        if agent_id:
            agents.pop(agent_id, None)


@app.websocket("/ws/client")
async def client_endpoint(ws: WebSocket):
    await ws.accept()
    client_id = str(uuid.uuid4())[:8]
    try:
        raw = await ws.receive_text()
        msg = json.loads(raw)
        if msg.get("token") != CLIENT_TOKEN:
            await ws.send_text(json.dumps({"status": "error", "msg": "неверный токен клиента"}))
            await ws.close()
            return

        clients[client_id] = ws
        print(f"[+] Клиент подключён: {client_id}")
        await ws.send_text(json.dumps({
            "status": "ok",
            "client_id": client_id,
            "agents": list(agents.keys()),
        }))

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            target = msg.get("agent_id")
            if target and target in agents:
                await agents[target].send_text(raw)
            elif agents:
                first = next(iter(agents.values()))
                await first.send_text(raw)
            else:
                await ws.send_text(json.dumps({
                    "status": "error", "msg": "нет подключённых агентов"
                }))

    except WebSocketDisconnect:
        print(f"[-] Клиент отключён: {client_id}")
    finally:
        clients.pop(client_id, None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)