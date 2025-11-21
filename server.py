import os
import json
import asyncio
from aiohttp import web
import aiohttp
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
# index.html を返す
# ================================
async def index(request):
    return web.FileResponse("templates/index.html")

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

                # ----------------------------
                # ready（待ち部屋入る）
                # ----------------------------
                if action == "ready":
                    gameid = data["gameid"]
                    user["action"] = "waiting"
                    user["gameid"] = gameid
                    server_status["waiting"][gameid] = user
                    await notify_status()

                # ----------------------------
                # invite（招待）
                # ----------------------------
                elif action == "invite":
                    session = data["session"]
                    user["action"] = "invite"
                    user["session"] = session
                    server_status["invites"][session] = user
                    await notify_status()

                # ----------------------------
                # start（ゲーム開始）
                # ----------------------------
                elif action == "start":
                    target = server_status["waiting"].get(data["gameid"])
                    if target:
                        msg = json.dumps({"type": "start"})
                        await target["ws"].send_str(msg)
                        await ws.send_str(msg)

                # ----------------------------
                # play（譜面送信）
                # ----------------------------
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

    # =============================
    # finally（全修正版）
    # =============================
    finally:
        if user in server_status["users"]:
            server_status["users"].remove(user)

        # waiting の後始末
        if user.get("action") == "waiting" and "gameid" in user:
            gameid = user.get("gameid")
            if gameid in server_status["waiting"]:
                del server_status["waiting"][gameid]

        # invite の後始末
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

    # ルート
    app.router.add_get("/", index)

    # WebSocket
    app.router.add_get("/ws", connection)

    # healthcheck
    app.router.add_get("/healthcheck", healthcheck)

    # Render 用ポート
    port = int(os.environ.get("PORT", 8080))

    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
