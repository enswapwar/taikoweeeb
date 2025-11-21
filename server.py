import os
import json
import asyncio
from aiohttp import web
import aiohttp
import aiohttp_jinja2
import jinja2
import traceback

# ================================
# グローバル状態
# ================================
server_status = {
    "users": [],
    "waiting": {},
    "invites": {}
}

# ================================
# WebSocket コネクション処理
# ================================
async def connection(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    user = {"ws": ws, "action": None}
    server_status["users"].append(user)

    async def notify_status():
        msg = json.dumps({
            "type": "status",
            "users": len(server_status["users"]),
            "waiting": list(server_status["waiting"].keys())
        })
        for u in server_status["users"]:
            ws_u = u.get("ws")
            if ws_u is not None and not ws_u.closed:
                await ws_u.send_str(msg)

    await notify_status()

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except:
                    continue

                action = data.get("action")

                # 待機
                if action == "ready":
                    gameid = data["gameid"]
                    user["action"] = "waiting"
                    user["gameid"] = gameid
                    server_status["waiting"][gameid] = user
                    await notify_status()

                # 招待
                elif action == "invite":
                    session = data["session"]
                    user["action"] = "invite"
                    user["session"] = session
                    server_status["invites"][session] = user
                    await notify_status()

                # ゲーム開始
                elif action == "start":
                    target = server_status["waiting"].get(data["gameid"])
                    if target:
                        msg_json = json.dumps({"type": "start"})
                        await target["ws"].send_str(msg_json)
                        await ws.send_str(msg_json)

                # 譜面送信
                elif action == "play":
                    session = data.get("session")
                    target = server_status["invites"].get(session)
                    if target and "ws" in target:
                        await target["ws"].send_str(json.dumps({
                            "type": "play",
                            "score": data.get("score"),
                            "combo": data.get("combo")
                        }))

    except Exception as e:
        print("Error in websocket:", e)
        traceback.print_exc()

    finally:
        if user in server_status["users"]:
            server_status["users"].remove(user)
        if user.get("action") == "waiting" and "gameid" in user:
            server_status["waiting"].pop(user["gameid"], None)
        if user.get("action") == "invite" and "session" in user:
            server_status["invites"].pop(user["session"], None)
        await notify_status()

    return ws

# ================================
# index.html を返す（Jinja2）
# ================================
@aiohttp_jinja2.template('index.html')
async def index(request):
    return {
        "version": {
            "commit": "f7617c1b7492e30011a1f08e8f3a023839aa41bd",
            "commit_short": "f7617c1",
            "url": "/",
            "version": "8.31.23"
        },
        "config": {
            "assets_baseurl": "./assets/"
        }
    }

# ================================
# healthcheck
# ================================
async def healthcheck(request):
    return web.Response(text="OK")

# ================================
# Web アプリ起動
# ================================
def main():
    app = web.Application()

    # Jinja2 設定
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

    # ルート
    app.router.add_get("/", index)

    # WebSocket
    app.router.add_get("/ws", connection)

    # healthcheck
    app.router.add_get("/healthcheck", healthcheck)

    # API
    app.router.add_static('/api/', path='./api/', show_index=False)
    app.router.add_get("/api/config", lambda r: web.FileResponse('./api/config.json'))
    app.router.add_get("/api/categories", lambda r: web.FileResponse('./api/categories.json'))
    app.router.add_get("/api/genres", lambda r: web.FileResponse('./api/genres.json'))
    app.router.add_get("/api/songs", lambda r: web.FileResponse('./api/songs.json'))

    # /src/ と /assets/ を公開
    app.router.add_static('/src/', path='./src/', show_index=False)
    app.router.add_static('/assets/', path='./assets/', show_index=False)

    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
