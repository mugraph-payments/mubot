import json
import asyncio
from typing import AsyncGenerator
from websockets.legacy.client import connect, WebSocketClientProtocol
from litellm import completion

WEBSOCKET_URI = "ws://localhost:8765"
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2:1b"

async def get_streaming_llm_response(message: str) -> AsyncGenerator[str, None]:
    try:
        response = completion(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": message}],
            api_base=OLLAMA_API_BASE,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception:
        yield "Sorry, I encountered an error. Please try again."

async def send_message(websocket: WebSocketClientProtocol, corr_id: str, sender: str, message: str) -> None:
    msg_content = [{"msgContent": {"type": "text", "text": message}}]
    cmd = f"/_send @{sender} live=on json {json.dumps(msg_content)}"
    await websocket.send(json.dumps({"corrId": corr_id, "cmd": cmd}))

async def send_edit(websocket: WebSocketClientProtocol, corr_id: str, sender: str, new_text: str) -> None:
    update_content = {"type": "text", "text": new_text}
    cmd = f"/_update item @{sender} {corr_id} live=on json {json.dumps(update_content)}"
    await websocket.send(json.dumps({"corrId": corr_id, "cmd": cmd}))

async def process_incoming_message(websocket: WebSocketClientProtocol, raw_message: str) -> None:
    try:
        data = json.loads(raw_message)
        resp = data.get("resp", {})
        if resp.get("type") != "newChatItems" or not resp.get("chatItems"):
            return

        chat_item = resp["chatItems"][0]
        if chat_item.get("chatItem", {}).get("chatDir", {}).get("type") != "directRcv":
            return

        meta = chat_item.get("chatItem", {}).get("meta", {})
        content = chat_item.get("chatItem", {}).get("content", {}).get("msgContent", {})
        contact = chat_item.get("chatInfo", {}).get("contact", {})

        item_id = meta.get("itemId")
        text = content.get("text")
        sender = contact.get("contactId")

        if not all([item_id, text, sender]):
            return

        corr_id = str(item_id + 1)
        buffer = []
        accumulated_text = []
        first_message = True

        async for chunk in get_streaming_llm_response(text):
            if not chunk:
                continue

            buffer.append(chunk)
            if any(chunk.endswith(end) for end in ('.', '!', '?')):
                current_text = ''.join(buffer).strip()
                accumulated_text.append(current_text)
                buffer = []

                if first_message:
                    await send_message(websocket, corr_id, sender, current_text)
                    first_message = False
                else:
                    await send_edit(websocket, corr_id, sender, ' '.join(accumulated_text))

                await asyncio.sleep(0.05)

        if buffer:
            final_text = ''.join(buffer).strip()
            accumulated_text.append(final_text)

            if first_message:
                await send_message(websocket, corr_id, sender, final_text)
            else:
                await send_edit(websocket, corr_id, sender, ' '.join(accumulated_text))

    except Exception as e:
        print(f"Error processing message: {e}")

async def main() -> None:
    while True:
        try:
            async with connect(WEBSOCKET_URI) as websocket:
                while True:
                    raw_msg = await websocket.recv()
                    await process_incoming_message(websocket, raw_msg)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
