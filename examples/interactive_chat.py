"""
17 — Interactive Chat

A terminal REPL that maintains conversation continuity across turns.
Commands:
  new / reset  — start a fresh conversation
  lang en/id   — switch response language
  exit / quit  — quit
"""

import asyncio

from brave_api import BraveClient, ClientConfig, StreamEventType


async def chat_loop() -> None:
    config = ClientConfig(language="id", ui_lang="id-id", country="id")

    print("=== Brave API Interactive Chat ===")
    print("Commands: 'exit' to quit | 'new' to reset | 'lang en/id' to switch language")
    print()

    conv_id: str | None = None
    sym_key: str | None = None
    language = "id"
    ui_lang = "id-id"

    async with BraveClient(config) as client:
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not query:
                continue

            if query.lower() in {"exit", "quit", "q", "keluar"}:
                print("Goodbye!")
                break

            if query.lower() in {"new", "reset", "baru"}:
                conv_id = None
                sym_key = None
                print("[New conversation started]\n")
                continue

            if query.lower().startswith("lang "):
                code = query[5:].strip().lower()
                if code == "en":
                    language, ui_lang = "en", "en-us"
                    print("[Language switched to English]\n")
                elif code == "id":
                    language, ui_lang = "id", "id-id"
                    print("[Language switched to Indonesian]\n")
                else:
                    print(f"[Unknown language code: {code!r}]\n")
                continue

            # Build conversation kwargs
            kwargs: dict = dict(language=language, ui_lang=ui_lang)
            if conv_id and sym_key:
                kwargs["conversation_id"] = conv_id
                kwargs["symmetric_key"] = sym_key

            try:
                conv = await client.conversation(query, **kwargs)

                print("Brave: ", end="", flush=True)
                async for event in conv.stream_events():
                    if event.type is StreamEventType.TEXT_DELTA:
                        print(event.delta, end="", flush=True)
                    elif event.type is StreamEventType.TEXT_STOP:
                        print()

                # Persist conversation identity for the next turn
                conv_id = conv.id
                sym_key = conv.symmetric_key
                print()

            except Exception as e:
                print(f"\n[ERROR] {e}\n")
                conv_id = None
                sym_key = None


asyncio.run(chat_loop())
