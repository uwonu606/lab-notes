import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("three_stages", Path(__file__).parent / "01_three_stages.py")
three_stages = module_from_spec(spec)
spec.loader.exec_module(three_stages)

original_ask = three_stages.ask

COPY_EXACTLY = (
    "Earlier answers for this passage are given below as JSON. "
    "When an event you write is the same event as one in \"event_entity\", "
    "copy that \"Event\" sentence exactly, character for character."
)


def ask_with_earlier_json():
    earlier = {}

    def ask(model, stage, passage):
        if stage == "event_relation":
            shown = json.dumps(earlier, ensure_ascii=False, indent=2)
            passage = f"{passage}\n\n{COPY_EXACTLY}\n{shown}"
            print("=== 질문 3 에 덧붙인 것\n" + COPY_EXACTLY + "\n" + shown)
        raw = original_ask(model, stage, passage)
        if stage in ("entity_relation", "event_entity"):
            earlier[stage], _ = three_stages.parse_or_empty(raw)
        return raw

    return ask


if __name__ == "__main__":
    three_stages.ask = ask_with_earlier_json()
    three_stages.main(*sys.argv[1:4])
