"""Translate resolved scene segments into Manim Community Edition objects."""
import json
import os
import sys
from pathlib import Path

import numpy as np
from manim import (
    Circle, Ellipse, Line, Polygon, Rectangle, Scene, SVGMobject, Text, UpdateFromAlphaFunc,
    VGroup, VMobject, linear, tempconfig,
)
from manimpango import list_fonts


def choose_font():
    fonts = set(list_fonts())
    override = os.environ.get("MATHSCENE_KOREAN_FONT")
    if override:
        if override not in fonts:
            raise RuntimeError(f"Requested font is not installed: {override}")
        return override
    return next((name for name in ("Apple SD Gothic Neo", "Noto Sans CJK KR", "Noto Sans KR",
                                   "Malgun Gothic", "NanumGothic", "Nanum Gothic") if name in fonts), "sans-serif")


class MathLayer(Scene):
    def __init__(self, data, work):
        self.lesson = data["lesson"]
        self.palette = data["palette"]
        self.segments = data["segments"]
        self.work = work
        self.w = self.lesson["canvas"]["width"]
        self.h = self.lesson["canvas"]["height"]
        self.unit = 8 / self.h
        self.font = choose_font()
        super().__init__()

    def point(self, x, y):
        return np.array([(x - self.w / 2) * self.unit, (self.h / 2 - y) * self.unit, 0])

    def place(self, item, x, y, align):
        dx = {"left": 1, "right": -1, "center": 0}[align] * item.width / 2
        return item.move_to(self.point(x, y) + [dx, 0, 0])

    def text(self, value, size, color):
        return Text(value, font=self.font, font_size=size * self.unit * 96, color=color,
                    disable_ligatures=True)

    def layer(self, source):
        kind = source["type"]
        color = self.palette[source.get("color", "foreground")]
        fill = self.palette[source["fill"]] if "fill" in source else color
        stroke = source.get("width", 2.5) * self.unit * 90
        if kind in {"text", "formula"}:
            size = source.get("size", 32)
            if kind == "text":
                item = self.text(source["text"], size, color)
            else:
                item = SVGMobject(self.work / source["file"])
                item.set(height=size * source["heightEm"] * self.unit * 1.2)
                item.set_fill(color, opacity=1)
            return self.place(item, source["x"], source["y"], source.get("align", "left"))
        if kind == "circle":
            return Circle(radius=source["r"] * self.unit, color=color, stroke_width=stroke,
                          fill_color=fill, fill_opacity=int("fill" in source)).move_to(
                self.point(source["x"], source["y"])
            )
        if kind == "ellipse":
            item = Ellipse(width=2 * source["rx"] * self.unit, height=2 * source["ry"] * self.unit,
                           color=color, stroke_width=stroke, fill_color=fill, fill_opacity=int("fill" in source))
            return item.move_to(self.point(source["x"], source["y"]))
        if kind == "rect":
            w, h = source["w"], source["h"]
            if not w or not h:
                return VMobject()
            item = Rectangle(width=w * self.unit, height=h * self.unit, color=color,
                             stroke_width=stroke, fill_color=fill, fill_opacity=int("fill" in source))
            return item.move_to(self.point(source["x"] + w / 2, source["y"] + h / 2))
        if kind == "polygon":
            return Polygon(*(self.point(*p) for p in source["points"]), color=color,
                           stroke_width=stroke, fill_color=fill, fill_opacity=int("fill" in source))
        if kind in {"gaussian", "polyline"}:
            item = VMobject(color=color, stroke_width=stroke)
            return item.set_points_as_corners([self.point(*p) for p in source["points"]])
        start = self.point(source["x1"], source["y1"])
        end = self.point(source["x2"], source["y2"])
        line = Line(start, end, color=color, stroke_width=stroke)
        arrow = source.get("arrow")
        if arrow:
            tip = Polygon(*(self.point(*p) for p in arrow), stroke_width=0, fill_color=color, fill_opacity=1)
            return VGroup(line, tip)
        return line

    def header(self, index):
        title = self.place(self.text(self.lesson["scenes"][index]["title"], .0159 * self.w,
                                     self.palette["white"]), .033 * self.w, .086 * self.h, "left")
        step = self.place(self.text(f"{index + 1} / {len(self.lesson['scenes'])}", .00725 * self.w,
                                    self.palette["teal"]), .967 * self.w, .086 * self.h, "right")
        divider = Line(self.point(.0325 * self.w, .1565 * self.h),
                       self.point(.9675 * self.w, .1565 * self.h), color=self.palette["grid"], stroke_width=1)
        if title.get_right()[0] >= step.get_left()[0] - 0.1 or title.get_bottom()[1] < divider.get_y():
            raise ValueError(f"scene {index + 1}: title overlaps counter or divider")
        return [title, step, divider]

    def get_moving_and_static_mobjects(self, animations):
        # Cairo otherwise keeps the original children of a moving group in its
        # list. Keep the groups intact to draw only the current frame's children.
        return list(self.mobjects), []

    def construct(self):
        fps = self.lesson["canvas"]["fps"]
        max_x, max_y = self.w * self.unit / 2, 4
        previous = None
        rendered = {}

        def checked(source):
            key = json.dumps(source, sort_keys=True)
            if key not in rendered:
                item = self.layer(source)
                left, right, bottom, top = (item.get_left()[0], item.get_right()[0],
                                             item.get_bottom()[1], item.get_top()[1])
                if left < -max_x or right > max_x or bottom < -max_y or top > max_y:
                    raise ValueError(f"{self.lesson['scenes'][index]['id']}/{source['id']} outside video frame")
                if len(rendered) >= 1200:
                    rendered.clear()
                rendered[key] = item
            return rendered[key]

        for segment in self.segments:
            index = segment["scene"]
            if index != previous:
                self.clear()
                self.add(*self.header(index))
                previous = index
                rendered = {}
            layers = VGroup()
            animated = []
            for layer in segment["layers"]:
                if "animationFrames" in layer:
                    path = VGroup()
                    animated.append((path, layer["animationFrames"]))
                    layers.add(path)
                else:
                    layers.add(checked(layer))
            self.add(layers)
            frames = segment["frames"]
            if animated:
                def update(_group, alpha):
                    frame = min(round(alpha * frames), frames - 1)
                    for path, snapshots in animated:
                        sample = snapshots[frame]
                        path.submobjects = [] if sample is None else [checked(sample)]

                # Cairo samples an exclusive end time. Keep exactly the authored frame count.
                self.play(UpdateFromAlphaFunc(layers, update, rate_func=linear,
                                               run_time=(frames - .001) / fps))
            else:
                self.wait((frames + .001) / fps, frozen_frame=True)
            self.remove(layers)


def main():
    work, width, height = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    data = json.loads((work / "segments.json").read_text(encoding="utf-8"))
    fps = data["lesson"]["canvas"]["fps"]
    target = work / "math.mp4"
    with tempconfig({"renderer": "cairo", "media_dir": str(work / "manim"), "output_file": str(target),
                     "pixel_width": width, "pixel_height": height, "frame_rate": fps,
                     "frame_width": data["lesson"]["canvas"]["width"] * 8 / data["lesson"]["canvas"]["height"],
                     "frame_height": 8, "background_color": data["palette"]["background"],
                     "write_to_movie": True, "disable_caching": True, "progress_bar": "none",
                     "verbosity": "WARNING"}):
        MathLayer(data, work).render()
    if not target.is_file():
        raise RuntimeError(f"Manim did not write {target}")


if __name__ == "__main__":
    main()
