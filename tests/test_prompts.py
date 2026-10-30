import hashlib
import json


def load():
    return json.load(open("bench/prompts.json", encoding="utf-8"))


def test_protocol_frozen():
    d = load()
    assert d["protocol_version"] == "v1"
    assert d["seeds"] == [42, 1337, 20261030]


def test_exactly_three_prompts_with_frozen_ids_and_text():
    d = load()
    assert [p["id"] for p in d["prompts"]] == [
        "p1-zh-scene",
        "p2-en-scene",
        "p3-poster-text",
    ]
    h = hashlib.sha256(
        json.dumps(d["prompts"], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    assert h == PROMPT_SET_SHA256


PROMPT_SET_SHA256 = "e7937fc56f1e37209ddeb4703e36b5ff0fb9fb9bda957821889c7cc6331efe93"
