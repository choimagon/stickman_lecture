"""Load a data-only lesson and verify timeline and supported math assertions."""
import json
import math
import operator
import re
from importlib.resources import files
from itertools import product
from functools import lru_cache
from pathlib import Path

import numpy as np
import sympy as sp
from jsonschema import Draft202012Validator

RESOURCES = files("mathscene").joinpath("resources")
ARITY = {
    "add": (2, 24), "sub": (2, 2), "mul": (2, 24), "div": (2, 2),
    "max": (2, 24), "pow": (2, 2), "sqrt": (1, 1), "exp": (1, 1),
    "lt": (2, 2), "select": (3, 3), "round": (1, 2), "concat": (1, 24),
}
FUNCTIONS = {
    "add": sum, "sub": operator.sub, "mul": math.prod, "div": operator.truediv,
    "max": lambda values: max(values), "pow": math.pow, "sqrt": math.sqrt,
    "exp": math.exp, "lt": operator.lt,
}
VARIADIC = {"add", "mul", "max"}
BINDABLE = {"x", "y", "x1", "y1", "x2", "y2", "w", "h", "r", "width",
            "size", "scale", "text", "tex", "mean", "sigma", "bubble", "fill", "color"}
NUMERIC_FIELDS = BINDABLE - {"text", "tex", "bubble", "fill", "color"}
COLORS = {"blue", "amber", "teal", "rose", "white", "muted", "grid", "ink"}
# Server-side TeX never receives raw input. These browser MathJax extensions are excluded too.
UNSAFE_TEX = re.compile(r"\\(?:require|input|include|write|openout|href|url|html\w*|style|class|cssId|def|gdef|edef|newcommand|renewcommand)\b", re.I)


class SceneError(ValueError):
    pass


@lru_cache
def schema_validator():
    return Draft202012Validator(json.loads(RESOURCES.joinpath("schema.json").read_text(encoding="utf-8")))


def js_string(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def expression(expr, variables, *, symbolic=False):
    if not isinstance(expr, list):
        if isinstance(expr, str):
            if symbolic and expr not in variables:
                raise SceneError(f"undeclared expression symbol: {expr}")
            return variables.get(expr, expr)
        return sp.Rational(str(expr)) if symbolic else expr

    name, *args = expr
    lo, hi = ARITY[name]
    if not lo <= len(args) <= hi:
        raise SceneError(f"invalid operand count for {name}: {len(args)}")
    if name == "select":
        if symbolic:
            raise SceneError("select is only supported in numeric expressions")
        condition, yes, no = args
        return expression(yes if expression(condition, variables) else no, variables)

    values = [expression(arg, variables, symbolic=symbolic) for arg in args]
    if symbolic:
        operations = {"add": sp.Add, "sub": operator.sub, "mul": sp.Mul,
                      "div": operator.truediv, "pow": sp.Pow, "sqrt": sp.sqrt,
                      "exp": sp.exp, "max": sp.Max}
        if name not in operations:
            raise SceneError(f"unsupported symbolic operation: {name}")
        return operations[name](*values)
    if name == "concat":
        return "".join(map(js_string, values))
    if name == "round":
        places = values[1] if len(values) == 2 else 0
        if type(places) is not int or not -12 <= places <= 12:
            raise SceneError("round precision must be an integer from -12 to 12")
        scale = 10 ** places
        return math.floor(values[0] * scale + 0.5) / scale
    if any(type(value) not in (int, float) for value in values):
        raise SceneError(f"{name} expects numeric operands")
    result = FUNCTIONS[name](values) if name in VARIADIC else FUNCTIONS[name](*values)
    if not math.isfinite(result):
        raise SceneError(f"nonfinite result for {name}")
    return result


def require_unique(values, context):
    if len(set(values)) != len(values):
        raise SceneError(f"duplicate {context}")


def require_frame(value, fps, path):
    frames = round(value * fps)
    if not math.isclose(value * fps, frames, abs_tol=1e-7):
        raise SceneError(f"{path}: {value}s does not align with {fps} fps")
    return frames


def numeric_contexts(controls):
    defaults = {c["id"]: c["default"] for c in controls}
    yield defaults
    if len(controls) <= 4:
        for values in product(*[(c["min"], c["max"]) for c in controls]):
            yield dict(zip(defaults, values))
    else:
        for c in controls:
            for bound in ("min", "max"):
                yield {**defaults, c["id"]: c[bound]}


def verify_bindings(layer, controls, location):
    bindings = layer.get("bind", {})
    for name in bindings:
        if name not in BINDABLE or name not in layer:
            raise SceneError(f"{location}: binding requires a supported base field: {name}")
    try:
        for context in numeric_contexts(controls):
            resolved = {**layer, **{k: expression(e, context) for k, e in bindings.items()}}
            for k in bindings:
                value = resolved[k]
                if k in NUMERIC_FIELDS:
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise SceneError(f"binding {k} does not return a finite number")
                    collapsed_rect = layer["type"] == "rect" and k in {"w", "h"} and value == 0
                    if k in {"w", "h", "r", "size", "scale", "width", "sigma"} and value <= 0 and not collapsed_rect:
                        raise SceneError(f"binding {k} must be positive")
                elif k in {"fill", "color"}:
                    if not isinstance(value, str) or value not in COLORS:
                        raise SceneError(f"binding {k} does not return a theme color")
                elif not isinstance(value, str):
                    raise SceneError(f"binding {k} does not return text")
            if layer["type"] == "formula" and UNSAFE_TEX.search(resolved["tex"]):
                raise SceneError("formula contains an unsupported TeX command")
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise SceneError(f"{location}: {exc}") from exc


def variables_in(expr, names):
    if isinstance(expr, list):
        return set().union(*(variables_in(part, names) for part in expr[1:]))
    return {expr} & names if isinstance(expr, str) else set()


def verify_scene(lesson):
    errors = sorted(schema_validator().iter_errors(lesson), key=lambda err: str(err.json_path))
    if errors:
        details = "\n".join(f"{e.json_path}: {e.message}" for e in errors[:10])
        raise SceneError(details)

    definitions = [entry["symbol"] for entry in lesson["definitions"]]
    require_unique(definitions, "symbol definition")
    scenes = lesson["scenes"]
    require_unique([scene["id"] for scene in scenes], "scene ID")
    fps = lesson["canvas"]["fps"]
    end = 0
    for scene in scenes:
        sid = scene["id"]
        if require_frame(scene["start"], fps, sid) != end:
            raise SceneError(f"{sid}: scene intervals must be contiguous from 0")
        end += require_frame(scene["duration"], fps, sid)
        if scene["duration"] < 1 / fps:
            raise SceneError(f"{sid}: scene must last at least one frame")
        layers = {layer["id"]: layer for layer in scene["layers"]}
        require_unique([layer["id"] for layer in scene["layers"]], f"layer ID in {sid}")
        controls = scene.get("interactions", [])
        require_unique([control["id"] for control in controls], f"control ID in {sid}")
        referred = set()
        for layer in layers.values():
            unknown = set(layer.get("symbols", [])) - set(definitions)
            if unknown:
                raise SceneError(f"{sid}/{layer['id']}: undefined symbols {sorted(unknown)}")
            if layer["type"] == "gaussian" and layer["min"] >= layer["max"]:
                raise SceneError(f"{sid}/{layer['id']}: gaussian min must be smaller than max")
            verify_bindings(layer, controls, f"{sid}/{layer['id']}")
            for binding in layer.get("bind", {}).values():
                referred.update(variables_in(binding, {c["id"] for c in controls}))
        for control in controls:
            lo, hi, initial = (control[k] for k in ("min", "max", "default"))
            step = control["step"]
            slots = ((initial - lo) / step, (hi - lo) / step)
            if not lo <= initial <= hi or not lo < hi or not all(math.isclose(n, round(n), abs_tol=1e-7) for n in slots):
                raise SceneError(f"{sid}/{control['id']}: invalid slider interval, step or default")
            if control["id"] not in referred:
                raise SceneError(f"{sid}/{control['id']}: slider has no layer binding")
        last = -1
        for event in scene["events"]:
            at = require_frame(event["at"], fps, f"{sid}/event")
            if at < last or event["at"] >= scene["duration"]:
                raise SceneError(f"{sid}: events must be sorted and inside the scene")
            last = at
            target = layers.get(event["target"])
            if target is None:
                raise SceneError(f"{sid}: event target does not exist: {event['target']}")
            if event["action"] == "gesture" and target["type"] != "stick":
                raise SceneError(f"{sid}: gesture target must be a stick layer")
    if end != require_frame(lesson["duration"], fps, "duration"):
        raise SceneError("lesson duration does not match the end of the last scene")
    return verify_checks(lesson)


def verify_checks(lesson):
    results = []
    scenes = {scene["id"]: scene for scene in lesson["scenes"]}
    for index, check in enumerate(lesson.get("checks", [])):
        kind = check["kind"]
        try:
            if kind == "sample":
                scene = scenes[check["scene"]]
                controls = {c["id"]: c for c in scene.get("interactions", [])}
                if not set(check["inputs"]) <= controls.keys():
                    raise SceneError("sample names an unknown slider")
                for name, value in check["inputs"].items():
                    if not controls[name]["min"] <= value <= controls[name]["max"]:
                        raise SceneError(f"sample is outside the range for {name}")
                context = {**{k: c["default"] for k, c in controls.items()}, **check["inputs"]}
                actual = expression(check["actual"], context)
                passed = bool(np.isclose(actual, check["expected"], rtol=1e-7, atol=1e-9))
            elif kind == "equivalent":
                symbols = {s: sp.Symbol(s, real=True) for s in check["symbols"]}
                left, right = (expression(check[k], symbols, symbolic=True) for k in ("left", "right"))
                actual = str(sp.simplify(left - right))
                passed = actual == "0"
            else:
                a, b = check["left"], check["right"]
                actual = [a[0], b[1]] if a[1] == b[0] else None
                passed = actual == check["expected"]
        except (ArithmeticError, TypeError, ValueError, KeyError) as exc:
            raise SceneError(f"math check {index + 1} ({kind}): {exc}") from exc
        if not passed:
            raise SceneError(f"math check {index + 1} ({kind}) failed: got {actual}")
        results.append({"kind": kind, "actual": actual, "passed": True})
    return results


def load_scene(path):
    def reject_constant(value):
        raise SceneError(f"invalid JSON number: {value}")

    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise SceneError("nonfinite JSON number")
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)

    try:
        lesson = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)
        finite(lesson)
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        raise SceneError(str(exc)) from exc
    return lesson, verify_scene(lesson)
