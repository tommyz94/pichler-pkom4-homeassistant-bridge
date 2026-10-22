import json
from pathlib import Path

from custom_components.pichler_pkom4_local.number import DESCRIPTIONS
from custom_components.pichler_pkom4_local.select import OPTIONS
from custom_components.pichler_pkom4_local.sensor import SENSORS

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/pichler_pkom4_local"


def test_hacs_layout_and_metadata():
    assert [
        p.name
        for p in (ROOT / "custom_components").iterdir()
        if p.is_dir() and not p.name.startswith("_")
    ] == ["pichler_pkom4_local"]
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert {"domain", "name", "version", "documentation", "issue_tracker", "codeowners"}.issubset(
        manifest
    )
    assert manifest["domain"] == COMPONENT.name
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == ["genvexnabto==1.5.4"]
    assert manifest["iot_class"] == "local_polling"
    assert json.loads((ROOT / "hacs.json").read_text())["render_readme"] is True


def test_entity_translations_cover_all_platforms():
    for language in ["en", "it"]:
        entities = json.loads((COMPONENT / "translations" / f"{language}.json").read_text())[
            "entity"
        ]
        for platform, descriptions in [("sensor", SENSORS), ("number", DESCRIPTIONS)]:
            for description in descriptions:
                assert description.translation_key in entities[platform]
        for key, options in OPTIONS.items():
            assert set(entities["select"][key.lower()]["state"]) == set(options)
        assert {"hotwater_fast_heating", "hotwater_e_heating"}.issubset(entities["switch"])
        assert "holiday_end" in entities["date"]
