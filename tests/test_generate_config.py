import importlib.util
from pathlib import Path

import pytest

# phase1-diffusers contains a dash: not importable as a package. Load the
# module by file path (generate.py keeps heavy imports inside main() so this
# works without torch installed).
MODULE_PATH = Path(__file__).resolve().parents[1] / "phase1-diffusers" / "generate.py"


def load_generate():
    spec = importlib.util.spec_from_file_location("p1_generate", MODULE_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_resolve_prompt_ids():
    gen = load_generate()
    for pid in ("p1-zh-scene", "p2-en-scene", "p3-poster-text"):
        text, negative = gen.resolve_prompt(pid)
        assert len(text) > 10
        assert negative == ""


def test_resolve_prompt_unknown_id():
    gen = load_generate()
    with pytest.raises(KeyError):
        gen.resolve_prompt("no-such-id")


def test_parse_args_exclusive():
    gen = load_generate()
    with pytest.raises(SystemExit):
        gen.parse_args(["--prompt-id", "p1-zh-scene", "--prompt", "hello"])


def test_defaults():
    gen = load_generate()
    ns = gen.parse_args(["--prompt-id", "p1-zh-scene"])
    assert ns.width == 2048
    assert ns.height == 2048
    assert ns.steps == 40
    assert ns.seed == 42
    assert ns.precision == "bf16"
    assert ns.out == "results/raw/"
