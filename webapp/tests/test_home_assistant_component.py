from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "smartlamp"


def test_home_assistant_manifest_declares_config_flow():
    payload = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert payload["domain"] == "smartlamp"
    assert payload["config_flow"] is True
    assert "light.py" in {path.name for path in INTEGRATION_DIR.iterdir()}


def test_home_assistant_translation_files_exist():
    en_payload = json.loads((INTEGRATION_DIR / "translations" / "en.json").read_text(encoding="utf-8"))
    zh_payload = json.loads(
        (INTEGRATION_DIR / "translations" / "zh-Hans.json").read_text(encoding="utf-8")
    )

    assert en_payload["config"]["step"]["user"]["data"]["base_url"] == "Webapp URL"
    assert zh_payload["config"]["step"]["user"]["data"]["base_url"] == "Webapp 地址"
