import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("three_stages", Path(__file__).parent / "01_three_stages.py")
three_stages = module_from_spec(spec)
spec.loader.exec_module(three_stages)

OFFICIAL_TYPES = "Identify temporal and causal relationships between the events using the following types: before, after, at the same time, because, and as a result."
WIDER_TYPES = "Identify temporal, causal, and logical relationships between the events using the following types: before, after, at the same time, because, as a result, but, in order to, and if."


def widen_event_relation_types():
    instructions = three_stages.TRIPLE_INSTRUCTIONS["en"]
    official = instructions["event_relation"]
    if OFFICIAL_TYPES not in official:
        raise SystemExit("공식 질문 3 지시문에서 관계 목록 문장을 찾지 못했다")
    instructions["event_relation"] = official.replace(OFFICIAL_TYPES, WIDER_TYPES)
    print("=== 질문 3 관계 목록\n" + WIDER_TYPES)


if __name__ == "__main__":
    widen_event_relation_types()
    three_stages.main(*sys.argv[1:4])
