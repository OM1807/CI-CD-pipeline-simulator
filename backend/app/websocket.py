from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
import os
import asyncio

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ws_router = APIRouter()

@ws_router.websocket("/builds/{build_id}/logs")
async def websocket_endpoint(websocket: WebSocket, build_id: str):
    await websocket.accept()
    redis = Redis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    channel = f"build-logs:{build_id}"
    await pubsub.subscribe(channel)
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = message['data'].decode('utf-8')
                await websocket.send_text(data)
                if data == "__EOF__":
                    break
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await redis.aclose()
