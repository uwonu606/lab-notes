import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("three_stages", Path(__file__).parent / "01_three_stages.py")
three_stages = module_from_spec(spec)
spec.loader.exec_module(three_stages)

original_ask = three_stages.ask
instructions = three_stages.TRIPLE_INSTRUCTIONS["en"]


def merged_instruction():
    parts = [f'"{stage}": {instructions[stage].rsplit("Here is the passage:", 1)[0].strip()}' for stage in three_stages.STAGES]
    keys = ", ".join(f'"{stage}"' for stage in three_stages.STAGES)
    return (
        "Answer the three tasks below for the same passage in one reply. "
        f"Return one JSON object with exactly these keys: {keys}. "
        "Each key holds the JSON array that its task asks for.\n\n"
        + "\n\n".join(parts)
        + "\nHere is the passage:"
    )


def one_call_ask():
    replies = {}

    def ask(model, stage, passage):
        if not replies:
            three_stages.TRIPLE_INSTRUCTIONS["en"]["merged"] = merged_instruction()
            raw = original_ask(model, "merged", passage)
            start, end = raw.find("{"), raw.rfind("}")
            try:
                replies.update(json.loads(raw[start : end + 1]))
            except ValueError:
                replies["_unparsed"] = raw
            print("=== 한 번에 물은 원답\n" + raw)
        return json.dumps(replies.get(stage, []), ensure_ascii=False)

    return ask


if __name__ == "__main__":
    three_stages.ask = one_call_ask()
    three_stages.main(*sys.argv[1:4])
