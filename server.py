import os
import json
import asyncio
import traceback
from aiohttp import web
import aiohttp
import aiohttp_jinja2
import jinja2

# ================================
# グローバル状態
# ================================
server_status = {
    "users": [],
    "waiting": {},
    "invites": {}
}

# ================================
# 全ユーザーにステータス送信
# ================================
async def notify_status():
    msg = json.dumps({
        "type": "status",
        "users": len(server_status["users"]),
        "waiting": list(server_status["waiting"].keys())
    })
    for u in server_status["users"]:
        ws = u.get("ws")
        if ws is not None and not ws.closed:
            await ws.send_str(msg)

# ================================
# WebSocket コネクション処理
# ================================
async def connection(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    user = {"ws": ws, "action": None}
    server_status["users"].append(user)
    await notify_status()

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except:
                    continue

                action = data.get("action")

                if action == "ready":
                    gameid = data["gameid"]
                    user["action"] = "waiting"
                    user["gameid"] = gameid
                    server_status["waiting"][gameid] = user
                    await notify_status()

                elif action == "invite":
                    session = data["session"]
                    user["action"] = "invite"
                    user["session"] = session
                    server_status["invites"][session] = user
                    await notify_status()

                elif action == "start":
                    target = server_status["waiting"].get(data["gameid"])
                    if target:
                        msg = json.dumps({"type": "start"})
                        await target["ws"].send_str(msg)
                        await ws.send_str(msg)

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
            gameid = user["gameid"]
            if gameid in server_status["waiting"]:
                del server_status["waiting"][gameid]
        if user.get("action") == "invite" and "session" in user:
            session = user["session"]
            if session in server_status["invites"]:
                del server_status["invites"][session]
        await notify_status()

    return ws

# ================================
# Web アプリ起動
# ================================
def main():
    app = web.Application()

    # Jinja2 設定
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

    # index.html をレンダリング
    @aiohttp_jinja2.template('index.html')
    async def index(request):
        with open('./api/config.json', encoding='utf-8') as f:
            config = json.load(f)
        version = config.get("_version", {})
        return {"version": version, "config": config}

    # API: config.json
    async def api_config(request):
        return web.FileResponse("./api/config.json")

    # API: categories.json
    async def api_categories(request):
        return web.FileResponse("./api/categories.json")

    # API: genres.json
    async def api_genres(request):
        return web.FileResponse("./api/genres.json")

    # API: songs.json
    async def api_songs(request):
        return web.FileResponse("./api/songs.json")

    # ================================
    # ルーター設定
    # ================================
    app.router.add_get("/", index)
    app.router.add_get("/ws", connection)
    app.router.add_get("/healthcheck", lambda r: web.Response(text="OK"))

    app.router.add_get("/api/config", api_config)
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/genres", api_genres)
    app.router.add_get("/api/songs", api_songs)

    app.router.add_static('/api/', path='./api/', show_index=False)
    app.router.add_static('/src/', path='./src/', show_index=False)
    app.router.add_static('/assets/', path='./assets/', show_index=False)

    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
