#!/usr/bin/env python3

import argparse
import asyncio
import json
import random
import os
from aiohttp import web, WSMsgType  # WSMsgType を使って受信メッセージの種類を判定

# health check ハンドラ
async def healthcheck(request):
    return web.Response(text="OK")

# 環境変数 PORT のデフォルト
default_port = int(os.environ.get("PORT", 34802))

# CLI 引数
parser = argparse.ArgumentParser(description='Run the taiko-web multiplayer server.')
parser.add_argument('port', type=int, metavar='PORT', nargs='?', default=default_port)
parser.add_argument('-b', '--bind-address', default='0.0.0.0', help='Bind server to address.')
parser.add_argument('-o', '--allow-origin', action='append', help='Limit incoming connections to the specified origin. Can be specified multiple times.')
args = parser.parse_args()
args.port = int(os.environ.get("PORT", args.port))

# サーバー状態
server_status = {
    "waiting": {},
    "users": [],
    "invites": {}
}

consonants = "bcdfghjklmnpqrstvwxyz"

# メッセージを JSON にするユーティリティ
def msgobj(t, v=None):
    return json.dumps({"type": t, "value": v} if v is not None else {"type": t})

# 待ち一覧を返すイベント
def status_event():
    value = [{"id": id, "diff": u["diff"]} for id, u in server_status["waiting"].items()]
    return msgobj("users", value)

# 招待コード生成
def get_invite():
    return "".join(random.choice(consonants) for _ in range(5))

# 全 ready ユーザーに通知
async def notify_status():
    msg = status_event()
    tasks = []
    for u in server_status["users"]:
        if u.get("action") == "ready" and "ws" in u:
            tasks.append(u["ws"].send_str(msg))
    if tasks:
        await asyncio.gather(*tasks)

# WebSocket ハンドラ
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    user = {
        "ws": ws,
        "action": "ready",
        "session": False,
        "name": None,
        "don": None
    }
    server_status["users"].append(user)

    # 接続直後に現在の待ち一覧を送る
    await ws.send_str(status_event())

    try:
        # 正しいパターン: ws から受け取るのは WSMessage、msg.type を確認して msg.data を読む
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                # テキスト以外（PING/PONG/CLOSE 等）は無視
                continue

            try:
                data = json.loads(msg.data)
            except Exception:
                data = {}

            msg_type = data.get("type")
            value = data.get("value")
            action = user.get("action")

            # ========== READY ==========
            if action == "ready":
                if msg_type == "join":
                    if not value:
                        continue

                    wid = value.get("id")
                    diff = value.get("diff")
                    user["name"] = value.get("name")
                    user["don"] = value.get("don")

                    if not wid or not diff:
                        continue

                    waiting = server_status["waiting"]

                    if wid not in waiting:
                        user["action"] = "waiting"
                        user["gameid"] = wid
                        waiting[wid] = {"user": user, "diff": diff}
                        await ws.send_str(msgobj("waiting"))
                    else:
                        other = waiting[wid]["user"]
                        other_diff = waiting[wid]["diff"]
                        del waiting[wid]

                        if "ws" in other:
                            user["action"] = "loading"
                            other["action"] = "loading"
                            user["other_user"] = other
                            other["other_user"] = user
                            user["player"] = 2
                            other["player"] = 1

                            await asyncio.gather(
                                ws.send_str(msgobj("gameload", {"diff": other_diff, "player": 2})),
                                other["ws"].send_str(msgobj("gameload", {"diff": diff, "player": 1})),
                                ws.send_str(msgobj("name", {"name": other["name"], "don": other["don"]})),
                                other["ws"].send_str(msgobj("name", {"name": user["name"], "don": user["don"]}))
                            )
                        else:
                            user["action"] = "waiting"
                            user["gameid"] = wid
                            waiting[wid] = {"user": user, "diff": diff}
                            await ws.send_str(msgobj("waiting"))

                    await notify_status()

                elif msg_type == "invite":
                    if value and value.get("id") is None:
                        code = get_invite()
                        server_status["invites"][code] = user
                        user["action"] = "invite"
                        user["session"] = code
                        user["name"] = value.get("name")
                        user["don"] = value.get("don")
                        await ws.send_str(msgobj("invite", code))

                    elif value and value.get("id") in server_status["invites"]:
                        other = server_status["invites"][value["id"]]
                        del server_status["invites"][value["id"]]

                        user["other_user"] = other
                        other["other_user"] = user
                        user["action"] = "invite"
                        user["session"] = value["id"]
                        user["player"] = 2
                        other["player"] = 1

                        await asyncio.gather(
                            ws.send_str(msgobj("session", {"player": 2})),
                            other["ws"].send_str(msgobj("session", {"player": 1})),
                            ws.send_str(msgobj("invite")),
                            ws.send_str(msgobj("name", {"name": other["name"], "don": other["don"]})),
                            other["ws"].send_str(msgobj("name", {"name": user["name"], "don": user["don"]}))
                        )
                    else:
                        await ws.send_str(msgobj("gameend"))

            # =================
            # waiting/loading/loaded
            # =================
            elif action in ("waiting", "loading", "loaded"):
                if msg_type == "leave":
                    if user["session"]:
                        if "other_user" in user and "ws" in user["other_user"]:
                            user["action"] = "songsel"
                            await asyncio.gather(
                                ws.send_str(msgobj("left")),
                                user["other_user"]["ws"].send_str(msgobj("users", []))
                            )
                        else:
                            user["action"] = "ready"
                            user["session"] = False
                            await asyncio.gather(
                                ws.send_str(msgobj("gameend")),
                                ws.send_str(status_event())
                            )
                    else:
                        gid = user.get("gameid")
                        if gid in server_status["waiting"]:
                            del server_status["waiting"][gid]
                        user["action"] = "ready"
                        await asyncio.gather(
                            ws.send_str(msgobj("left")),
                            notify_status()
                        )

                if action == "loading" and msg_type == "gamestart":
                    user["action"] = "loaded"
                    other = user.get("other_user")
                    if other and other.get("action") == "loaded" and "ws" in other:
                        user["action"] = "playing"
                        other["action"] = "playing"
                        await asyncio.gather(
                            ws.send_str(msgobj("gamestart")),
                            other["ws"].send_str(msgobj("gamestart"))
                        )

            # ========== PLAYING ==========
            elif action == "playing":
                other = user.get("other_user")
                if other and "ws" in other:
                    if msg_type in ("note", "drumroll", "branch", "gameresults"):
                        await other["ws"].send_str(msgobj(msg_type, value))

                    elif msg_type == "songsel" and user["session"]:
                        user["action"] = other["action"] = "songsel"
                        await asyncio.gather(
                            ws.send_str(msgobj("songsel")),
                            ws.send_str(msgobj("users", [])),
                            other["ws"].send_str(msgobj("songsel")),
                            other["ws"].send_str(msgobj("users", []))
                        )

                    elif msg_type == "gameend":
                        user["action"] = "ready"
                        other["action"] = "ready"
                        await asyncio.gather(
                            ws.send_str(msgobj("gameend")),
                            other["ws"].send_str(msgobj("gameend")),
                            ws.send_str(status_event()),
                            other["ws"].send_str(status_event())
                        )
                        del other["other_user"]
                        del user["other_user"]
                else:
                    user["action"] = "ready"
                    user["session"] = False
                    await ws.send_str(msgobj("gameend"))
                    await ws.send_str(status_event())

            # ========== INVITE ==========
            elif action == "invite":
                if msg_type == "leave":
                    if user["session"] in server_status["invites"]:
                        del server_status["invites"][user["session"]]
                    user["action"] = "ready"
                    user["session"] = False

                    other = user.get("other_user")
                    if other and "ws" in other:
                        other["action"] = "ready"
                        other["session"] = False
                        await asyncio.gather(
                            ws.send_str(msgobj("left")),
                            ws.send_str(status_event()),
                            other["ws"].send_str(msgobj("gameend")),
                            other["ws"].send_str(status_event())
                        )
                    else:
                        await asyncio.gather(
                            ws.send_str(msgobj("left")),
                            ws.send_str(status_event())
                        )

    finally:
        # 切断されたユーザーをリストから削除
        if user in server_status["users"]:
            server_status["users"].remove(user)

    return ws

def main():
    app = web.Application()
    app.router.add_get('/health', healthcheck)
    app.router.add_get('/ws', ws_handler)
    web.run_app(app, host=args.bind_address, port=args.port)

if __name__ == "__main__":
    main()
