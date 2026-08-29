from __future__ import annotations

import asyncio
import json
import os

import websockets


CORE_WS_URL = os.getenv("AGENT_CORE_WS_URL", "ws://127.0.0.1:8765/ws")


async def receive_json(websocket: websockets.ClientConnection) -> dict[str, object]:
    message = await websocket.recv()
    payload = json.loads(message)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object, got: {payload!r}")
    return payload


async def receive_type(
    websocket: websockets.ClientConnection,
    event_type: str,
) -> dict[str, object]:
    async with asyncio.timeout(5):
        while True:
            payload = await receive_json(websocket)
            if payload.get("type") == event_type:
                return payload


async def main() -> None:
    async with (
        websockets.connect(CORE_WS_URL, proxy=None) as avatar,
        websockets.connect(CORE_WS_URL, proxy=None) as ui,
    ):
        for websocket, role in ((avatar, "avatar"), (ui, "ui")):
            status = await receive_type(websocket, "core.status")
            if status.get("status") != "online":
                raise RuntimeError(f"Core did not report online: {status}")
            await websocket.send(json.dumps({"type": "client.hello", "role": role}))
            ready = await receive_type(websocket, "client.ready")
            if ready.get("role") != role:
                raise RuntimeError(f"Unexpected role acknowledgement: {ready}")

        await avatar.send(
            json.dumps(
                {
                    "type": "avatar.interaction",
                    "event": "avatar.clicked",
                    "payload": {"x": 240, "y": 360},
                }
            )
        )
        menu_event = await receive_type(ui, "ui.menu.toggle")
        menu_payload = menu_event.get("payload")
        if not isinstance(menu_payload, dict) or menu_payload.get("x") != 240:
            raise RuntimeError(f"Menu event was not routed to UI: {menu_event}")

        await ui.send(
            json.dumps(
                {
                    "type": "avatar.command",
                    "event": "avatar.wave",
                    "payload": {},
                }
            )
        )
        command = await receive_type(avatar, "avatar.command")
        if command.get("event") != "avatar.wave":
            raise RuntimeError(f"Avatar command was not routed to Avatar: {command}")

        await ui.send(json.dumps({"type": "chat.message", "text": "桥接状态验证"}))
        states: list[str] = []
        response_received = False
        async with asyncio.timeout(8):
            while states[-3:] != ["thinking", "speaking", "idle"]:
                payload = await receive_json(ui)
                if payload.get("type") == "agent.state":
                    states.append(str(payload.get("state", "")))
                elif payload.get("type") == "chat.response":
                    response_received = True

        if not response_received:
            raise RuntimeError("chat.response was not routed to UI")

    print(
        json.dumps(
            {
                "bridge": "ok",
                "states": states,
                "chat_response": response_received,
                "menu_routing": True,
                "avatar_command_routing": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
