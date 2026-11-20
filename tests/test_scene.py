import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mathscene.scene import RESOURCES, SceneError, load_scene, verify_scene

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture
def mlp():
    return load_scene(EXAMPLES / "mlp" / "scene.json")[0]


@pytest.mark.parametrize("slug", ["mlp", "kalman-filter", "linear-algebra", "rfs-intuition"])
def test_example_assertions(slug):
    lesson, checks = load_scene(EXAMPLES / slug / "scene.json")
    assert len(lesson["scenes"]) == 6
    assert checks and all(row["passed"] for row in checks)


@pytest.mark.parametrize("problem,expected", [
    ("gap", "intervals must be contiguous"),
    ("event_time", "events must be sorted and inside"),
    ("event_target", "target does not exist"),
    ("undefined_symbol", "undefined symbols"),
    ("wrong_math", "math check 1"),
    ("wrong_shape", "math check 4"),
    ("unsafe_tex", "unsupported TeX command"),
    ("broken_binding", "finite number"),
    ("no_binding", "slider has no layer binding"),
])
def test_incorrect_lessons_fail(mlp, problem, expected):
    if problem == "gap":
        mlp["scenes"][1]["start"] += 1
    if problem == "event_time":
        scene = mlp["scenes"][0]
        scene["events"][-1]["at"] = scene["duration"]
    if problem == "event_target":
        mlp["scenes"][0]["events"][0]["target"] = "not_a_layer"
    if problem in ("undefined_symbol", "unsafe_tex"):
        formula = next(layer for layer in mlp["scenes"][3]["layers"] if layer["type"] == "formula")
        if problem == "undefined_symbol":
            formula["symbols"].append("not_defined")
        else:
            formula["tex"] = r"\input{private}"
    if problem == "wrong_math":
        mlp["checks"][0]["expected"] += 1
    if problem == "wrong_shape":
        mlp["checks"].append({"kind":"shape", "left":[2, 3], "right":[2, 1], "expected":[2, 1]})
    if problem == "broken_binding":
        layer = next(layer for layer in mlp["scenes"][4]["layers"] if "bind" in layer)
        layer["bind"]["size"] = "missing_identifier"
    if problem == "no_binding":
        for layer in mlp["scenes"][4]["layers"]:
            layer.pop("bind", None)
    with pytest.raises(SceneError, match=expected):
        verify_scene(mlp)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed to check browser state")
def test_mlp_interaction_and_gesture_across_frames(mlp):
    core = RESOURCES / "web" / "core.js"
    script = """
      require(process.argv[1]);
      const data = JSON.parse(process.argv[2]);
      const before = MathScene.state(data, 0.5);
      const after = MathScene.state(data, 1.5);
      function get(scene, id) { return scene.layers.find(layer => layer.id === id); }
      const first = MathScene.state(data, 26, {x1: 0});
      const last = MathScene.state(data, 26, {x1: 4});
      console.log(JSON.stringify({
        initialGesture: get(before, "teacher").weights.wave,
        finalGesture: get(after, "teacher").weights.point_right,
        firstText: get(first, "iy").text, lastText: get(last, "iy").text,
        firstBar: get(first, "bar_h1").w, lastBar: get(last, "bar_h1").w,
        nextScene: MathScene.state(data, 30).scene.id,
      }));
    """
    run = subprocess.run(["node", "-e", script, str(core), json.dumps(mlp)], check=True,
                         capture_output=True, text=True)
    actual = json.loads(run.stdout)
    assert actual["initialGesture"] == actual["finalGesture"] == 1
    assert actual["firstText"].endswith("3")
    assert actual["lastText"].endswith("6")
    assert actual["firstBar"] == 0 < actual["lastBar"]
    assert actual["nextScene"] == "recap"
