import json
import shutil
import subprocess

import pytest

from mathscene.scene import RESOURCES, verify_scene


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is needed to pace the lesson")
def test_pacing_matches_bubble_length_without_clipping_a_crossing_draw():
    teacher = {"id": "teacher", "type": "stick", "x": 205, "y": 550, "pose": "idle"}
    arrow = {"id": "arrow", "type": "vector", "x1": 430, "x2": 1000, "y1": 400, "y2": 400}
    scene = {
        "id": "short-first", "stage": "why", "title": "짧으면 일찍 넘기기", "start": 0, "duration": 8,
        "learning_goal": "말풍선과 화살표", "narration": "다음.",
        "layers": [teacher, arrow],
        "events": [
            {"at": 0, "action": "draw", "target": "arrow", "duration": 1},
            {"at": 4, "action": "speak", "target": "teacher",
             "value": "이제 화살표의 시작점부터 도착점까지 어떤 방향으로 가는지 읽어 봅시다."},
        ],
    }
    crossing = {**scene, "id": "crossing", "start": 8, "events": [
        {"at": 3, "action": "draw", "target": "arrow", "duration": 3},
        {"at": 4, "action": "speak", "target": "teacher", "value": "끝."},
    ]}
    lesson = {
        "version": "0.1", "title": "타이밍 예제", "locale": "ko-KR", "audience": "beginner",
        "duration": 16, "canvas": {"width": 1280, "height": 720, "fps": 30},
        "theme": "stick-studio", "definitions": [], "scenes": [scene, crossing], "exports": ["video"],
    }
    module = (RESOURCES / "pacing.mjs").as_uri()
    script = """
      import {readFileSync} from "node:fs";
      const {paceLesson} = await import(process.argv[1]);
      console.log(JSON.stringify(paceLesson(JSON.parse(readFileSync(0, "utf8")))));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, module],
                            input=json.dumps(lesson), capture_output=True, text=True, check=True)
    adjusted = json.loads(result.stdout)
    verify_scene(adjusted)
    first, second = adjusted["scenes"]
    change_time = first["events"][1]["at"]
    assert 1.5 < change_time < 2
    assert first["duration"] - change_time > 4
    assert second["start"] == first["duration"]
    assert second["events"][1]["at"] == 4
    assert second["events"][0]["duration"] == 3 and second["duration"] > 6
