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
def test_math_example_assertions(slug):
    lesson, checks = load_scene(EXAMPLES / slug / "scene.json")
    assert {scene["stage"] for scene in lesson["scenes"]} == {
        "why", "intuition", "example", "equation", "insight", "recap",
    }
    assert checks and all(row["passed"] for row in checks)


def test_shape_example_uses_non_math_primitives():
    lesson, checks = load_scene(EXAMPLES / "shapes" / "scene.json")
    assert not checks
    traced = {
        next(layer["type"] for layer in scene["layers"] if layer["id"] == event["target"])
        for scene in lesson["scenes"] for event in scene["events"] if event["action"] == "draw"
    }
    assert traced >= {"ellipse", "polygon", "rect", "circle", "vector"}


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
    ("speech_target", "speak target must be a stick layer"),
    ("draw_target", "draw target must be a supported stroke"),
    ("draw_too_long", "draw must leave at least one completed frame"),
    ("draw_and_show", "use one draw event without show"),
])
def test_incorrect_lessons_fail(mlp, problem, expected):
    network = next(scene for scene in mlp["scenes"] if scene["id"] == "network")
    controls = next(scene for scene in mlp["scenes"] if scene["id"] == "insight")
    draw = next(event for event in network["events"] if event["action"] == "draw")
    if problem == "gap":
        mlp["scenes"][1]["start"] += 1
    if problem == "event_time":
        scene = mlp["scenes"][0]
        scene["events"][-1]["at"] = scene["duration"]
    if problem == "event_target":
        mlp["scenes"][0]["events"][0]["target"] = "not_a_layer"
    if problem in ("undefined_symbol", "unsafe_tex"):
        formula = next(layer for scene in mlp["scenes"] for layer in scene["layers"] if layer["type"] == "formula")
        if problem == "undefined_symbol":
            formula["symbols"].append("not_defined")
        else:
            formula["tex"] = r"\input{private}"
    if problem == "wrong_math":
        mlp["checks"][0]["expected"] += 1
    if problem == "wrong_shape":
        mlp["checks"].append({"kind": "shape", "left": [2, 3], "right": [2, 1], "expected": [2, 1]})
    if problem == "broken_binding":
        layer = next(layer for layer in controls["layers"] if "bind" in layer)
        layer["bind"]["size"] = "missing_identifier"
    if problem == "no_binding":
        for layer in controls["layers"]:
            layer.pop("bind", None)
    if problem == "speech_target":
        next(event for event in network["events"] if event["action"] == "speak")["target"] = "w11"
    if problem == "draw_target":
        draw["target"] = "lx1"
    if problem == "draw_too_long":
        draw["duration"] = network["duration"] - draw["at"]
    if problem == "draw_and_show":
        network["events"].insert(0, {"at": 0, "action": "show", "target": draw["target"]})
    with pytest.raises(SceneError, match=expected):
        verify_scene(mlp)


def run_browser_core(script, lesson=None):
    core = RESOURCES / "web" / "core.js"
    run = subprocess.run(["node", "-e", script, str(core)], input=json.dumps(lesson), check=True,
                         capture_output=True, text=True)
    return json.loads(run.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed to check browser state")
def test_mlp_interaction_arrow_and_speech_across_frames(mlp):
    actual = run_browser_core("""
      require(process.argv[1]);
      const data = JSON.parse(require("node:fs").readFileSync(0, "utf8"));
      const scene = id => data.scenes.find(s => s.id === id);
      const get = (state, id) => state.layers.find(layer => layer.id === id);
      const network = scene("network");
      const when = network.start + network.events.find(event => event.action === "draw").at;
      const before = MathScene.state(data, when - .5);
      const middle = MathScene.state(data, when + .5);
      const after = MathScene.state(data, when + 1.5);
      const first = MathScene.state(data, scene("insight").start + 1, {x1: 0});
      const last = MathScene.state(data, scene("insight").start + 1, {x1: 4});
      console.log(JSON.stringify({
        startsHidden: get(before, "w11") === undefined,
        atHalf: MathScene.geometry(get(middle, "w11")).x2,
        atEnd: MathScene.geometry(get(after, "w11")).x2,
        nextIsHidden: get(after, "w12") === undefined,
        speech: MathScene.speech(middle),
        firstText: get(first, "iy").text, lastText: get(last, "iy").text,
        firstBar: get(first, "bar_h1").w, lastBar: get(last, "bar_h1").w,
      }));
    """, mlp)
    assert actual["startsHidden"] and actual["nextIsHidden"]
    assert actual["atHalf"] == 645 < actual["atEnd"] == 755
    assert "+1" in actual["speech"]
    assert actual["firstText"] == "y = 3"
    assert actual["lastText"] == "y = 6"
    assert actual["firstBar"] == 0 < actual["lastBar"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed to sample geometry")
def test_shape_outline_precedes_fill_and_polyline_tracks_distance():
    actual = run_browser_core("""
      require(process.argv[1]);
      const rect = {type:"rect",x:20,y:10,w:100,h:60,fill:"surface"};
      const mid = MathScene.geometry({...rect,progress:.5});
      const done = MathScene.geometry({...rect,progress:1});
      const line = MathScene.geometry({type:"polyline",points:[[0,0],[10,0],[10,30]],progress:.5});
      console.log(JSON.stringify({mid,done,line}));
    """)
    assert actual["mid"]["type"] == "polyline"
    assert actual["mid"]["points"][-1] == [120, 70]
    assert actual["done"]["type"] == "rect" and actual["done"]["fill"] == "surface"
    assert actual["line"]["points"][-1] == [10, 10]
