"""
MuBot Ollama main module
"""

import json
import asyncio
import logging

from websockets.legacy.client import connect, WebSocketClientProtocol
from litellm import completion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBSOCKET_URI = "ws://localhost:3030"
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2:1b"


async def get_llm_response(message: str) -> str:
    """
    Obtain an LLM response from Ollama using LiteLLM's synchronous `completion`.
    """
    try:
        response = completion(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": message}],
            api_base=OLLAMA_API_BASE,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LiteLLM API error: {e}")
        raise


async def process_incoming_message(
    websocket: WebSocketClientProtocol, raw_message: str
) -> None:
    """
    Processes a single incoming raw message from the WebSocket,
    sends an LLM-generated response if applicable.
    """
    try:
        data = json.loads(raw_message)
        chat_item = data["resp"]["chatItems"][0]["chatItem"]

        # Ignore outgoing messages
        if chat_item["chatDir"]["type"] != "directRcv":
            return

        user_text = chat_item["content"]["msgContent"]["text"]
        logger.info(f"Received user message: {user_text}")

        logger.info("Fetching LLM response from Ollama...")
        llm_response = await get_llm_response(user_text)
        logger.info(f"LLM response: {llm_response}")

        response_data = {
            "corrId": "123",
            "cmd": f"@lucasnbarros_1 {llm_response}",
        }
        await websocket.send(json.dumps(response_data))
        logger.info("Response sent.")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def main() -> None:
    """
    Connect to the WebSocket server, continuously receive messages,
    and process them using `process_incoming_message`.
    """
    try:
        async with connect(WEBSOCKET_URI) as websocket:
            logger.info("Connected to WebSocket server.")

            while True:
                raw_msg = await websocket.recv()
                await process_incoming_message(websocket, raw_msg)

    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt.")
    except asyncio.CancelledError:
        logger.info("Task cancelled.")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
