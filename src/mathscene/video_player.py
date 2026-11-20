"""Create an offline chapter navigator for a rendered lecture."""
import json

from .scene import RESOURCES


def write_video_player(lesson, destination):
    data = {
        "title": lesson["title"], "locale": lesson["locale"],
        "width": lesson["canvas"]["width"], "height": lesson["canvas"]["height"],
        "scenes": [{"title": scene["title"], "start": scene["start"]} for scene in lesson["scenes"]],
    }
    # Escape HTML markup without changing the JSON value read by the browser.
    serialized = json.dumps(data, ensure_ascii=True).replace("<", r"\u003c")
    template = (RESOURCES / "video-player.html").read_text(encoding="utf-8")
    destination.write_text(template.replace("__STICKMAN_VIDEO_DATA__", serialized), encoding="utf-8")
