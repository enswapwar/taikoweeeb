import os
import json
import asyncio
from aiohttp import web
import aiohttp
import traceback
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
# 設定読み込み
# ================================
with open("./api/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

version_info = config["_version"]
assets_baseurl = config["assets_baseurl"]

# ================================
# index.html を返す（テンプレート処理）
# ================================
@aiohttp_jinja2.template("index.html")
async def index(request):
    # テンプレートに version と config を渡す
    return {
        "version": version_info,
        "config": config
    }

# ================================
# healthcheck
# ================================
async def healthcheck(request):
    return web.Response(text="OK")

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

    # user dict
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

                # ready（待ち部屋入る）
                if action == "ready":
                    gameid = data["gameid"]
                    user["action"] = "waiting"
                    user["gameid"] = gameid
                    server_status["waiting"][gameid] = user
                    await notify_status()

                # invite（招待）
                elif action == "invite":
                    session = data["session"]
                    user["action"] = "invite"
                    user["session"] = session
                    server_status["invites"][session] = user
                    await notify_status()

                # start（ゲーム開始）
                elif action == "start":
                    target = server_status["waiting"].get(data["gameid"])
                    if target:
                        msg_send = json.dumps({"type": "start"})
                        await target["ws"].send_str(msg_send)
                        await ws.send_str(msg_send)

                # play（譜面送信）
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

    # finally（クリーンアップ）
    finally:
        if user in server_status["users"]:
            server_status["users"].remove(user)

        if user.get("action") == "waiting" and "gameid" in user:
            gameid = user.get("gameid")
            if gameid in server_status["waiting"]:
                del server_status["waiting"][gameid]

        if user.get("action") == "invite" and "session" in user:
            session = user.get("session")
            if session in server_status["invites"]:
                del server_status["invites"][session]

        await notify_status()

    return ws

# ================================
# Web アプリ起動
# ================================
def main():
    app = web.Application()

    # Jinja2 テンプレート設定
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("./templates"))

    # ルート
    app.router.add_get("/", index)

    # API
    app.router.add_get("/api/config", lambda r: web.FileResponse("./api/config.json"))
    app.router.add_get("/api/categories", lambda r: web.FileResponse("./api/categories.json"))
    app.router.add_get("/api/genres", lambda r: web.FileResponse("./api/genres.json"))
    app.router.add_get("/api/songs", lambda r: web.FileResponse("./api/songs.json"))

    # 静的ファイル
    app.router.add_static('/src/', path='./src/', show_index=False)
    app.router.add_static('/assets/', path='./assets/', show_index=False)
    app.router.add_static('/api/', path='./api/', show_index=False)

    # WebSocket
    app.router.add_get("/ws", connection)

    # healthcheck
    app.router.add_get("/healthcheck", healthcheck)

    # Render 用ポート
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
