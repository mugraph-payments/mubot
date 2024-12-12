"""
MuBot Ollama main module
"""
from litellm import completion

def main() -> None:
    """Main entry point for the application"""

    # print("Hello World!")
    response = completion(
        model="ollama/llama3.2:1b",
        messages=[{ "content": "respond in 20 words. who are you?","role": "user"}],
        api_base="http://localhost:11434"
    )
    print(response)


if __name__ == "__main__":
    main()
