"""
MuBot Ollama main module
"""
import json
import asyncio
import uuid
from typing import Union
from websockets.legacy.client import connect, WebSocketClientProtocol
from litellm import completion

WEBSOCKET_URI = "ws://localhost:3030"
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2:1b"

async def get_llm_response(message: str) -> str:
    """Get an LLM response from Ollama."""
    try:
        response = completion(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": message}],
            api_base=OLLAMA_API_BASE,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception:
        return "Sorry, I encountered an error. Please try again."

async def process_incoming_message(websocket: WebSocketClientProtocol, raw_message: Union[str, bytes]) -> None:
    """Process incoming WebSocket message and send response if applicable."""
    try:
        # Convert bytes to str if necessary
        message_str = raw_message.decode() if isinstance(raw_message, bytes) else raw_message
        data = json.loads(message_str)

        if not (data.get("resp", {}).get("type") == "newChatItems" and
                "chatItems" in data.get("resp", {})):
            return

        chat_items = data["resp"]["chatItems"]
        if not chat_items:
            return

        chat_info = chat_items[0].get("chatInfo", {})
        chat_item = chat_items[0].get("chatItem", {})
        contact = chat_info.get("contact", {})

        if chat_item.get("chatDir", {}).get("type") != "directRcv":
            return

        msg_content = chat_item.get("content", {}).get("msgContent", {})
        if msg_content.get("type") != "text":
            return

        text = msg_content.get("text")
        if not text:
            return

        sender = contact.get("localDisplayName")
        if not sender:
            return

        llm_response = await get_llm_response(text)
        formatted_sender = f"'{sender}'" if ' ' in sender else sender
        formatted_response = f"@{formatted_sender} {llm_response}"

        response_data = {
            "corrId": str(uuid.uuid4()),
            "cmd": formatted_response
        }
        await websocket.send(json.dumps(response_data))

    except Exception:
        pass

async def main() -> None:
    """Run the main WebSocket client loop."""
    try:
        async with connect(WEBSOCKET_URI) as websocket:
            while True:
                raw_msg = await websocket.recv()
                await process_incoming_message(websocket, raw_msg)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass

if __name__ == "__main__":
    asyncio.run(main())
