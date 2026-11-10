import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from city_timelapse import main


def make_layout(tmp_path, second_origin):
    template = {"phases": [{"id": "frame", "ops": [
        {"fill": ["oak_stairs:north", [0, 0, 0], [1, 0, 0]]},
        {"set": ["log:x", [1, 0, 1]]},
    ]}]}
    (tmp_path / "plot.json").write_text(json.dumps(template))
    layout = {"duration": 4, "districts": [
        {"id": "first", "origin": [0, 0, 0], "blueprint": "plot.json"},
        {"id": "second", "origin": second_origin, "rotation": 90, "blueprint": "plot.json"},
    ]}
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(layout))
    return layout_path


def test_city_reuses_templates_with_rotated_placements(tmp_path):
    layout = make_layout(tmp_path, [6, 1, 4])
    out = tmp_path / "out"
    assert main([str(layout), "--out", str(out)]) == 0
    report = json.loads((out / "build-report.json").read_text())
    story = json.loads((out / "story.json").read_text())
    assert report["blockCount"] == 6
    assert [phase["id"] for phase in report["phases"]] == ["first-frame", "second-frame"]
    assert [(c["block"], c["place"]) for c in story["changes"][3:]] == [
        ("oak_stairs:west", [6, 1, 3]), ("oak_stairs:west", [6, 1, 4]), ("log:z", [7, 1, 3]),
    ]
    assert (out / "mix.wav").exists()
    assert (out / "city-blueprint.json").exists()


def test_city_refuses_overlap_between_districts(tmp_path, capsys):
    layout = make_layout(tmp_path, [0, 0, 0])
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as failure:
        main([str(layout), "--out", str(out)])
    assert failure.value.code == 2
    assert "duplicate voxel" in capsys.readouterr().err
    assert not (out / "story.json").exists()


def test_city_preserves_source_template_when_output_would_overwrite_it(tmp_path, capsys):
    layout = make_layout(tmp_path, [6, 1, 4])
    out = tmp_path / "out"
    out.mkdir()
    template = out / "story.json"
    (tmp_path / "plot.json").replace(template)
    original = template.read_bytes()
    data = json.loads(layout.read_text())
    for district in data["districts"]:
        district["blueprint"] = "out/story.json"
    layout.write_text(json.dumps(data))
    with pytest.raises(SystemExit) as failure:
        main([str(layout), "--out", str(out)])
    assert failure.value.code == 2
    assert "source layout and templates" in capsys.readouterr().err
    assert template.read_bytes() == original
