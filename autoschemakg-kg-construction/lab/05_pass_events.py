import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("three_stages", Path(__file__).parent / "01_three_stages.py")
three_stages = module_from_spec(spec)
spec.loader.exec_module(three_stages)

original_ask = three_stages.ask


def ask_with_stage2_events():
    stage2_events = []

    def ask(model, stage, passage):
        if stage == "event_relation" and stage2_events:
            shown = "\n".join(f"- {event}" for event in stage2_events)
            passage = f"{passage}\n\nEvents already extracted from this passage:\n{shown}"
            print("=== 질문 3 에 덧붙인 것\n" + shown)
        raw = original_ask(model, stage, passage)
        if stage == "event_entity":
            items, _ = three_stages.parse_or_empty(raw)
            stage2_events.extend(
                three_stages.clean_text(str(item.get("Event", ""))) for item in items if isinstance(item, dict) and item.get("Event")
            )
        return raw

    return ask


if __name__ == "__main__":
    three_stages.ask = ask_with_stage2_events()
    three_stages.main(*sys.argv[1:4])
