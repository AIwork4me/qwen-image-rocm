import pytest


def test_build_workflow_nodes():
    from bench.comfyui_client import build_workflow

    wf = build_workflow(
        unet="qwen_image_2.1_bf16.safetensors",
        clip="qwen3vl_8b_bf16.safetensors",
        vae="qwen_image_2.1_vae_bf16.safetensors",
        prompt="a cat",
        negative="",
        width=1024,
        height=1024,
        steps=40,
        seed=42,
        sampler="euler",
        scheduler="simple",
    )
    classes = {nid: node["class_type"] for nid, node in wf.items()}
    assert set(classes.values()) >= {
        "UNETLoader",
        "CLIPLoader",
        "VAELoader",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    }
    # two text encodes (positive + negative)
    assert list(classes.values()).count("CLIPTextEncode") == 2


def test_build_workflow_seed_mapping():
    from bench.comfyui_client import build_workflow

    wf = build_workflow(
        unet="u", clip="c", vae="v", prompt="p", negative="n",
        width=1024, height=1024, steps=40, seed=1337,
        sampler="euler", scheduler="simple",
    )
    ks = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
    assert ks["inputs"]["seed"] == 1337
    assert ks["inputs"]["steps"] == 40
    assert ks["inputs"]["sampler_name"] == "euler"
    assert ks["inputs"]["scheduler"] == "simple"
    assert ks["inputs"]["cfg"] == 1.0  # official Qwen-Image-2.1 default
    latent = [n for n in wf.values() if n["class_type"] == "EmptyLatentImage"][0]
    assert latent["inputs"]["width"] == 1024
    assert latent["inputs"]["height"] == 1024


def test_check_server_rejects_cpu(monkeypatch):
    from bench import comfyui_client as cc

    class FakeResp:
        def __init__(self, payload):
            self._p = payload

        def json(self):
            return self._p

    monkeypatch.setattr(
        cc, "_get", lambda url, timeout=10: FakeResp(
            {"devices": [{"name": "cpu", "type": "cpu"}]}
        )
    )
    with pytest.raises(RuntimeError, match="7900"):
        cc.check_server("http://127.0.0.1:8188")
