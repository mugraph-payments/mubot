import json
import asyncio
from typing import AsyncGenerator
from websockets.legacy.client import connect, WebSocketClientProtocol
from litellm import completion

from .tools import (
    FUNCTION_SCHEMAS,
    should_use_tools,
    extract_location,
    execute_function_call
)

WEBSOCKET_URI = "ws://localhost:8765"
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2:1b"

async def get_streaming_llm_response(message: str) -> AsyncGenerator[str, None]:
    use_tools = should_use_tools(message)

    if use_tools:
        location = extract_location(message)
        messages = [
            {
                "role": "system",
                "content": f"You are a weather assistant. When responding about temperature, "
                           f"always use the get_temperature function to fetch accurate data. "
                           f"The user is asking about the temperature in {location}. "
                           "Be concise and direct in your response."
            } if location else {},
            {"role": "user", "content": message}
        ]
    else:
        messages = [{"role": "user", "content": message}]

    messages = [msg for msg in messages if msg]

    buffer = ""
    response = completion(
        model=OLLAMA_MODEL,
        messages=messages,
        api_base=OLLAMA_API_BASE,
        stream=True,
        tools=FUNCTION_SCHEMAS if use_tools else None,
        tool_choice="auto" if use_tools else None
    )

    for chunk in response:
        if use_tools and chunk.choices and hasattr(chunk.choices[0].delta, 'tool_calls'):
            for tool_call in chunk.choices[0].delta.tool_calls or []:
                if hasattr(tool_call, 'function'):
                    try:
                        result = await execute_function_call({
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        })
                        yield f"{result}"
                    except Exception as e:
                        yield f"\nError executing function: {str(e)}\n"

        if chunk.choices and chunk.choices[0].delta.content:
            buffer += chunk.choices[0].delta.content

            if any(buffer.endswith(end) for end in ('.', '!', '?', '\n')):
                yield buffer
                buffer = ""

    if buffer:
        yield buffer

async def send_message(websocket: WebSocketClientProtocol, corr_id: str, sender: str, message: str) -> None:
    msg_content = [{"msgContent": {"type": "text", "text": message}}]
    cmd = f"/_send @{sender} live=on json {json.dumps(msg_content)}"
    await websocket.send(json.dumps({"corrId": corr_id, "cmd": cmd}))

async def send_edit(websocket: WebSocketClientProtocol, corr_id: str, sender: str, new_text: str) -> None:
    update_content = {"type": "text", "text": new_text}
    cmd = f"/_update item @{sender} {corr_id} live=on json {json.dumps(update_content)}"
    await websocket.send(json.dumps({"corrId": corr_id, "cmd": cmd}))

async def process_incoming_message(websocket: WebSocketClientProtocol, raw_message: str) -> None:
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
    accumulated_text = []
    first_message = True

    async for chunk in get_streaming_llm_response(text):
        if not chunk:
            continue

        accumulated_text.append(chunk)
        current_text = ' '.join(accumulated_text)

        if first_message:
            await send_message(websocket, corr_id, sender, current_text)
            first_message = False
        else:
            await send_edit(websocket, corr_id, sender, current_text)

        await asyncio.sleep(0.01)

async def main() -> None:
    while True:
        try:
            async with connect(WEBSOCKET_URI) as websocket:
                while True:
                    raw_msg = await websocket.recv()
                    await process_incoming_message(websocket, raw_msg)
        except Exception as e:
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
