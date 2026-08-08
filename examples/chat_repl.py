"""Interactive terminal chat with conversation continuity.

Type a question to get a streamed answer. Commands:

- ``/new``        start a fresh conversation
- ``/lang id``    switch the response language (``en`` or ``id``)
- ``/quit``       exit
"""

import asyncio

from brave_api import BraveClient, ClientConfig, StreamEventType

QUIT_COMMANDS = frozenset({"/quit", "/exit", "q"})


async def main() -> None:
    config = ClientConfig(language="en", ui_lang="en-us", country="us")
    language = "en"
    ui_lang = "en-us"
    conversation_id: str | None = None
    symmetric_key: str | None = None

    async with BraveClient(config) as client:
        print("Brave AI chat — type /new, /lang id, or /quit\n")
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not query:
                continue
            if query in QUIT_COMMANDS:
                break
            if query == "/new":
                conversation_id = None
                symmetric_key = None
                print("(new conversation)\n")
                continue
            if query.startswith("/lang"):
                _, _, code = query.partition(" ")
                language, ui_lang = (
                    ("id", "id-id") if code.strip().lower() == "id" else ("en", "en-us")
                )
                print(f"(language: {language})\n")
                continue

            conversation = await client.conversation(
                query,
                language=language,
                ui_lang=ui_lang,
                conversation_id=conversation_id,
                symmetric_key=symmetric_key,
            )
            print("Brave: ", end="", flush=True)
            async for event in conversation.stream_events():
                if event.type is StreamEventType.TEXT_DELTA:
                    print(event.delta, end="", flush=True)
            print("\n")

            conversation_id = conversation.id
            symmetric_key = conversation.symmetric_key


if __name__ == "__main__":
    asyncio.run(main())
