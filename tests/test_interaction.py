import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mathscene.scene import RESOURCES, SceneError, load_scene, verify_scene


DEMO = Path(__file__).resolve().parents[1] / "examples" / "stick-interaction" / "scene.json"


def test_tracks_and_touch_targets_are_validated():
    lesson, checks = load_scene(DEMO)
    assert checks[0]["actual"] == 10
    actor = next(layer for layer in lesson["scenes"][0]["layers"] if layer["type"] == "stick")
    actor["touch"]["target"] = "missing"
    with pytest.raises(SceneError, match="touch target"):
        verify_scene(lesson)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed to check shared visual state")
def test_one_value_connects_the_cart_hand_graph_and_slider():
    lesson, _checks = load_scene(DEMO)
    core = RESOURCES / "web" / "core.js"
    script = """
      require(process.argv[1]);
      const data = JSON.parse(require("node:fs").readFileSync(0, "utf8"));
      const sample = values => {
        const state = MathScene.state(data, 7.5, values);
        const get = id => state.layers.find(layer => layer.id === id);
        return {
          z: state.values.z, cart: get("cart").x, hand: get("teacher").contact.x,
          handle: get("handle").x, measure: get("measurement").x, estimate: get("estimate").x,
          speed: get("teacher").walk.speed, reading: get("reading").text,
        };
      };
      console.log(JSON.stringify([sample({}), sample({z:12})]));
    """
    run = subprocess.run(["node", "-e", script, str(core)], input=json.dumps(lesson), capture_output=True,
                         encoding="utf-8", check=True)
    moving, manual = json.loads(run.stdout)
    assert moving["z"] == 10 and moving["cart"] == 363 and moving["speed"] > 0
    assert moving["hand"] == moving["handle"] - 8
    assert (moving["measure"], moving["estimate"]) == (800, 700)
    assert manual["z"] == 12 and manual["cart"] == 423 and manual["speed"] == 0
    assert manual["hand"] == manual["handle"] - 8
    assert (manual["measure"], manual["estimate"]) == (1000, 800)
    assert manual["reading"].endswith("= 10")
