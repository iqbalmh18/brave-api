"""
15 — Raw Events Inspection

Inspect every event in result.raw_events after collect().
Useful for understanding what the server sent, debugging unexpected
behavior, or exploring undocumented event types.
"""

import asyncio
import json

from brave_api import BraveClient


async def main() -> None:
    async with BraveClient() as client:
        conv = await client.conversation("sejarah singkat perang dunia 2", language="id")
        result = await conv.collect()

    print(f"Total events : {len(result.raw_events)}")
    print(f"Answer       : {result.text[:200]}...")

    # Group events by type
    by_type: dict[str, list] = {}
    for ev in result.raw_events:
        by_type.setdefault(ev.raw_type, []).append(ev)

    print("\n=== Events by type ===")
    for t, evs in sorted(by_type.items()):
        print(f"  {t}: {len(evs)}x")

    # Sample TEXT_DELTA tokens
    text_deltas = by_type.get("text_delta", [])
    if text_deltas:
        print(f"\n=== TEXT_DELTA ({len(text_deltas)} tokens) ===")
        preview = "".join(e.delta for e in text_deltas[:10])
        print(f"  First 10: {preview!r} ...")

    # TOOL_USE — raw tool call requests from the server
    tool_evs = by_type.get("tool_use", [])
    print(f"\n=== TOOL_USE ({len(tool_evs)} events) ===")
    for ev in tool_evs:
        print(f"  id   : {ev.tool_id}")
        print(f"  name : {ev.tool_name}")
        print(f"  args : {json.dumps(ev.tool_arguments, ensure_ascii=False)[:150]}")

    # AUGMENT_WITH_TOOL_USE — enrichment results from run_tool
    aug_evs = by_type.get("augment_with_tool_use", [])
    print(f"\n=== AUGMENT_WITH_TOOL_USE ({len(aug_evs)} results) ===")
    for ev in aug_evs[:2]:
        sr = ev.payload.get("service_response", {})
        if isinstance(sr, dict):
            web = sr.get("web", {})
            if isinstance(web, dict):
                print(f"  query='{ev.payload.get('query', '')}' | "
                      f"web_results={len(web.get('results', []))}")

    # INITIAL_RESPONSE — first web results before tool calls
    init_evs = by_type.get("initial_response", [])
    if init_evs:
        print("\n=== INITIAL_RESPONSE ===")
        sr = init_evs[0].payload.get("service_response", {})
        if isinstance(sr, dict):
            web = sr.get("web", {})
            if isinstance(web, dict):
                print(f"  initial web results: {len(web.get('results', []))}")

    # DEBUG_LABELS — internal routing labels from Brave
    debug_evs = by_type.get("debug_labels", [])
    if debug_evs:
        print("\n=== DEBUG_LABELS ===")
        for label in debug_evs[0].payload.get("labels", []):
            print(f"  {label}")

    # FOLLOWUPS — suggested follow-up questions
    followup_evs = by_type.get("followups", [])
    if followup_evs:
        followups = followup_evs[0].payload.get("followups", [])
        print(f"\n=== FOLLOWUPS ({len(followups)}) ===")
        for f in followups[:5]:
            print(f"  - {f}")


asyncio.run(main())
