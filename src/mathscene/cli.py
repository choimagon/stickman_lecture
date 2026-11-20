"""StickMan Lecture CLI and export orchestration."""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

from .audio import bubble_cues, visual_cues, write_effect_track
from .narration import (NarrationError, VOICE_NAMES, check_voice, download_voice,
                        narration_minimums, synthesize_spans, write_narration)
from .scene import RESOURCES, SceneError, load_scene
from .video_player import write_video_player


class RenderError(RuntimeError):
    pass


def json_file(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def node_home(near=None):
    paths = [Path.cwd(), Path(__file__).resolve().parent]
    if near:
        paths.insert(0, near)
    explicit = os.environ.get("MATHSCENE_NODE_HOME")
    if explicit:
        paths.insert(0, Path(explicit).expanduser().resolve())
    for start in paths:
        for folder in (start, *start.parents):
            if all((folder / "node_modules" / package / "package.json").is_file()
                   for package in ("playwright", "katex", "mathjax-full")):
                return folder
    raise RenderError("Node dependencies not found. Run npm ci or set MATHSCENE_NODE_HOME.")


def executable(name):
    found = shutil.which(name)
    if not found:
        raise RenderError(f"{name} executable not found in PATH")
    return found


def run(stage, command, work):
    log = work / f"{stage}.log"
    with log.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps([str(arg) for arg in command], ensure_ascii=False) + "\n")
        stream.flush()
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-10:])
        raise RenderError(f"{stage} exited with code {result.returncode}. See {log}\n{tail}")


def bridge(stage, node, home, work, *args):
    run(stage, [node, str(RESOURCES / "bridge.mjs"), str(stage), str(home), *map(str, args)], work)


def build_web(lesson, node, home, work, narration=None):
    web = work / "web"
    web.mkdir()
    sources = RESOURCES / "web"
    for name in ("index.html", "style.css", "core.js", "stick-scene.js", "stick-scene.LICENSE.txt", "stick.js", "player.js"):
        shutil.copyfile(sources / name, web / name)
    serialized = json.dumps(lesson, ensure_ascii=True, allow_nan=False)
    script = "globalThis.MATHSCENE_LESSON = JSON.parse(" + json.dumps(serialized) + ");\n"
    if narration:
        shutil.copyfile(narration, web / "narration.wav")
        script += "globalThis.MATHSCENE_NARRATION = true;\n"
    (web / "scene-data.js").write_text(script, encoding="utf-8")
    package = home / "node_modules" / "katex"
    katex = package / "dist"
    vendor = web / "vendor"
    vendor.mkdir()
    for name in ("katex.min.css", "katex.min.js"):
        shutil.copyfile(katex / name, vendor / name)
    shutil.copytree(katex / "fonts", vendor / "fonts")
    shutil.copyfile(package / "LICENSE", vendor / "KATEX-LICENSE")
    screenshots = work / "web-frames"
    screenshots.mkdir()
    bridge("verify", node, home, work, web, screenshots, work / "web-preview.png")
    return {**json.loads((screenshots / "browser.json").read_text()), "hasNarration": bool(narration)}


def probe(ffprobe, video):
    result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                            capture_output=True, check=True, text=True)
    return json.loads(result.stdout)


def verify_video(ffprobe, file, width, height, fps, frames):
    info = probe(ffprobe, file)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    actual = (stream["width"], stream["height"], Fraction(stream["avg_frame_rate"]), int(stream["nb_frames"]))
    expected = (width, height, fps, frames)
    duration = float(stream["duration"])
    if actual != expected or abs(duration - frames / fps) > .001:
        raise RenderError(f"{file.name}: expected {expected}, found {actual} at {duration}s")
    return {"width": width, "height": height, "fps": fps, "frames": frames,
            "duration": duration, "codec": stream["codec_name"],
            "hasAudio": any(s["codec_type"] == "audio" for s in info["streams"])}


def timestamp(seconds):
    hours, rem = divmod(round(seconds * 1000), 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, milli = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milli:03}"


def write_srt(segments, fps, path):
    spans = []
    elapsed = 0
    for segment in segments:
        end = elapsed + segment["frames"]
        spoken = segment["speech"]
        if spans and spans[-1][1] == elapsed and spans[-1][2] == spoken:
            spans[-1] = (spans[-1][0], end, spoken)
        elif spoken:
            spans.append((elapsed, end, spoken))
        elapsed = end
    entries = [f"{i}\n{timestamp(start / fps)} --> {timestamp(end / fps)}\n{spoken}"
               for i, (start, end, spoken) in enumerate(spans, 1)]
    path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def build_video(lesson, scene_file, node, home, work, preview, audio, bubble_sound, visual_sound, narration=None):
    if importlib.util.find_spec("manim") is None:
        raise RenderError("ManimCE is missing. Install the mathscene[video] extra.")
    ffmpeg, ffprobe = executable("ffmpeg"), executable("ffprobe")
    width, height, fps = (lesson["canvas"][k] for k in ("width", "height", "fps"))
    if preview:
        width, height = max(2, width // 4 * 2), max(2, height // 4 * 2)
    frames = round(lesson["duration"] * fps)
    bridge("prepare", node, home, work, scene_file, work)
    segments = json.loads((work / "segments.json").read_text(encoding="utf-8"))["segments"]
    bubbles = bubble_cues(segments) if bubble_sound else []
    visuals = visual_cues(segments) if visual_sound else []
    cues = [(frame, "bubble") for frame in bubbles] + visuals
    with ThreadPoolExecutor(max_workers=2) as executor:
        manim = executor.submit(run, "manim", [sys.executable, "-m", "mathscene.manim_render", str(work),
                                               str(width), str(height)], work)
        capture = executor.submit(bridge, "capture", node, home, work, scene_file, work, width, height, ffmpeg)
        manim.result()
        capture.result()
    math_video = work / "math.mp4"
    stick_video = work / "overlay.mov"
    verify_video(ffprobe, math_video, width, height, fps, frames)
    alpha = verify_video(ffprobe, stick_video, width, height, fps, frames)
    if not any(s.get("pix_fmt") == "argb" for s in probe(ffprobe, stick_video)["streams"]):
        raise RenderError("Canvas overlay has no expected alpha channel")
    lesson_video = work / "lesson.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(math_video), "-i", str(stick_video)]
    filters = "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]"
    sound = []
    if narration:
        sound.append((narration, 1))
    if audio:
        sound.append((audio, .30 if narration else 1))
    if cues:
        effects = work / "effects.wav"
        write_effect_track(effects, cues, frames, fps)
        sound.append((effects, .34 if narration else .5 if audio else 1))
    for source, _gain in sound:
        command += ["-i", str(source)]
    if len(sound) > 1:
        parts = []
        for i, (_source, gain) in enumerate(sound):
            filters += f";[{i + 2}:a:0]volume={gain}[sound{i}]"
            parts.append(f"[sound{i}]")
        filters += (";" + "".join(parts) + f"amix=inputs={len(sound)}:duration=longest:normalize=0,"
                    "alimiter=limit=0.95:level=0:latency=1,apad[a]")
    command += ["-filter_complex", filters, "-map", "[v]", "-frames:v", str(frames),
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "19", "-movflags", "+faststart"]
    if sound:
        command += ["-map", "[a]" if len(sound) > 1 else "2:a:0"]
        if len(sound) == 1:
            command += ["-af", "apad"]
        command += ["-t", f"{frames / fps:.9f}", "-c:a", "aac"]
    run("composite", [*command, str(lesson_video)], work)
    report = verify_video(ffprobe, lesson_video, width, height, fps, frames)
    if report["hasAudio"] != bool(sound):
        raise RenderError("Unexpected audio track in the lesson")
    run("decode", [ffmpeg, "-v", "error", "-xerror", "-i", str(lesson_video), "-f", "null", "-"], work)
    reel = work / "video-frames"
    reel.mkdir()
    for i, scene in enumerate(lesson["scenes"]):
        time = scene["start"] + scene["duration"] * .94
        path = reel / f"{i + 1:02}-{scene['id']}.png"
        run(f"frame-{i + 1:02}", [ffmpeg, "-v", "error", "-y", "-ss", str(time), "-i", str(lesson_video),
                                  "-frames:v", "1", str(path)], work)
        if i == min(2, len(lesson["scenes"]) - 1):
            shutil.copyfile(path, work / "video-preview.png")
    write_srt(segments, fps, work / "captions.srt")
    write_video_player(lesson, work / "player.html")
    animated_frames = sum(part["frames"] for part in segments if part["drawing"])
    tracked_frames = sum(part["frames"] for part in segments if part["tracked"])
    return {**report, "overlay": alpha, "motion": json.loads((work / "motion.json").read_text()),
            "bubbleSoundCues": len(bubbles), "visualSoundCues": len(visuals), "drawFrames": animated_frames,
            "trackedFrames": tracked_frames, "hasNarration": bool(narration),
            "decoded": True, "screenshots": len(lesson["scenes"]), "htmlPlayer": "player.html"}


def storyboard(lesson, source_path, dest, paced=False):
    original = source_path.with_name("storyboard.md")
    if original.is_file() and original.resolve() != dest.resolve() and paced:
        rows = [f"# {lesson['title']}", "", "## 최종 영상 시간표", "",
                "| 시각 | 장면 |", "| --- | --- |"]
        for s in lesson["scenes"]:
            rows.append(f"| {timestamp(s['start']).split(',')[0]} | {s['title'].replace('|', '￨')} |")
        source = original.read_text(encoding="utf-8")
        if source.startswith("# "):
            source = source.split("\n", 1)[-1].lstrip()
        rows += ["", "## 제작 시 작성한 장면 계획", "", source]
        dest.write_text("\n".join(rows), encoding="utf-8")
        return
    if original.is_file():
        if original.resolve() != dest.resolve():
            shutil.copyfile(original, dest)
        return
    lines = [f"# {lesson['title']}", ""]
    for scene in lesson["scenes"]:
        lines += [f"## {scene['title']} ({scene['start']:g}초)", "", scene["learning_goal"], "", scene["narration"], ""]
    dest.write_text("\n".join(lines), encoding="utf-8")


def publish(source, dest, work):
    if dest.exists():
        dest.rename(work / f"previous-{dest.name}")
    source.rename(dest)


def render(args):
    scene_path = args.scene.resolve()
    lesson, checks = load_scene(scene_path)
    slug = scene_path.parent.name if scene_path.stem == "scene" else scene_path.stem
    slug = re.sub(r"[^\w.-]+", "-", slug).strip(".-") or "lesson"
    out = (args.out or Path("output") / slug).resolve()
    out.mkdir(parents=True, exist_ok=True)
    root = out / "_work"
    root.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=root))
    mode = args.mode
    wanted = ["web", "video"] if mode == "both" else [mode]
    report = {"ok": False, "mode": mode, "math": checks, "sceneCount": len(lesson["scenes"]),
              "timeline": [{"id": s["id"], "start": s["start"], "duration": s["duration"]} for s in lesson["scenes"]],
              "run": str(work.relative_to(out)), "exports": {}}
    prepared = work / "scene.json"
    json_file(prepared, lesson)
    paced = False
    try:
        node = executable("node")
        home = node_home(scene_path.parent)
        narration = None
        minimums = []
        if args.narration:
            speech_plan = work / "speech-plan.json"
            bridge("speech-plan", node, home, work, prepared, speech_plan)
            spans = json.loads(speech_plan.read_text(encoding="utf-8"))
            print(f"Synthesizing offline narration ({args.voice})", flush=True)
            clips, sample_rate = synthesize_spans(spans, lesson["locale"], args.voice)
            length_file = work / "speech-minimums.json"
            json_file(length_file, narration_minimums(clips, sample_rate))
            minimums = [length_file]
        if ("video" in wanted or args.narration) and not args.fixed_timing:
            source_duration = lesson["duration"]
            adjusted = work / "paced.json"
            bridge("pace", node, home, work, prepared, adjusted, *minimums)
            candidate, _ = load_scene(adjusted)
            if candidate != lesson:
                paced = True
                lesson = candidate
                json_file(prepared, lesson)
            report["pacing"] = {"sourceDuration": source_duration, "duration": lesson["duration"], "changed": paced}
            report["timeline"] = [{"id": s["id"], "start": s["start"], "duration": s["duration"]}
                                  for s in lesson["scenes"]]
        if args.narration:
            if paced:
                bridge("speech-plan", node, home, work, prepared, speech_plan)
                spans = json.loads(speech_plan.read_text(encoding="utf-8"))
            narration = work / "narration.wav"
            fps = lesson["canvas"]["fps"]
            write_narration(narration, spans, clips, round(lesson["duration"] * fps), fps, sample_rate)
            report["narration"] = {"voice": args.voice, "cues": len(spans), "sampleRate": sample_rate}
        for medium in wanted:
            stage = work / medium
            stage.mkdir()
            print(f"Rendering {medium}: {lesson['title']}", flush=True)
            try:
                if medium == "web":
                    detail = build_web(lesson, node, home, stage, narration)
                    publish(stage / "web", out / "web", work)
                    shutil.copyfile(stage / "web-preview.png", out / "web-preview.png")
                    if mode == "web":
                        shutil.copyfile(stage / "web-preview.png", out / "preview.png")
                else:
                    detail = build_video(lesson, prepared, node, home, stage, args.preview, args.audio,
                                         not (args.no_effects or args.no_bubble_sound), not args.no_effects,
                                         narration)
                    for name in ("lesson.mp4", "captions.srt", "player.html"):
                        publish(stage / name, out / name, work)
                    shutil.copyfile(stage / "video-preview.png", out / "preview.png")
                report["exports"][medium] = {"ok": True, **detail}
            except (OSError, RenderError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
                report["exports"][medium] = {"ok": False, "error": str(exc)}
                print(exc, file=sys.stderr)
        report["ok"] = all(r["ok"] for r in report["exports"].values())
    except (RenderError, SceneError, NarrationError) as exc:
        report["error"] = str(exc)
        print(exc, file=sys.stderr)
    finally:
        published_scene = out / "scene.json"
        if scene_path != published_scene.resolve():
            shutil.copyfile(prepared, published_scene)
        elif paced:
            published_scene = out / "rendered-scene.json"
            shutil.copyfile(prepared, published_scene)
        report["renderedScene"] = published_scene.name
        storyboard(lesson, scene_path, out / "storyboard.md", paced)
        json_file(out / "validation.json", report)
    print(f"Validation report: {out / 'validation.json'}")
    return int(not report["ok"])


def doctor(args):
    status = {"python": sys.version.split()[0], "node": shutil.which("node"),
              "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
    try:
        home = node_home()
        status["nodeHome"] = str(home)
        proc = subprocess.run([executable("node"), str(RESOURCES / "bridge.mjs"), "doctor", str(home)],
                              capture_output=True, text=True, check=False)
        status["browser"] = proc.stdout.strip() if proc.returncode == 0 else None
        if proc.returncode:
            status["browserError"] = proc.stderr.strip()
    except RenderError as exc:
        status["browser"] = None
        status["browserError"] = str(exc)
    status["manim"] = None
    if importlib.util.find_spec("manim"):
        try:
            import manim
            from .manim_render import choose_font
            status["manim"] = manim.__version__
            status["videoFont"] = choose_font()
        except (ImportError, OSError, RuntimeError) as exc:
            status["manimError"] = str(exc)
    if args.narration:
        try:
            _engine, directory = check_voice("F3")
            status["voiceModel"] = str(directory)
        except NarrationError as exc:
            status["voiceError"] = str(exc)
    required = ["node", "browser"] + (["ffmpeg", "ffprobe", "manim", "videoFont"] if args.video else [])
    if args.narration:
        required.append("voiceModel")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return int(not all(status.get(k) for k in required))


def validate(args):
    lesson, checks = load_scene(args.scene)
    print(json.dumps({"ok": True, "scenes": len(lesson["scenes"]), "math": checks}, ensure_ascii=False, indent=2))
    return 0


def voice_setup(_args):
    print(f"Offline voice model: {download_voice()}")
    return 0


def player(args):
    directory = args.directory.resolve()
    video = directory / "lesson.mp4"
    if not video.is_file():
        raise RenderError(f"No rendered video at {video}")
    scene_name = "scene.json"
    report = directory / "validation.json"
    if report.is_file():
        try:
            recorded = json.loads(report.read_text(encoding="utf-8")).get("renderedScene", scene_name)
        except (AttributeError, ValueError) as exc:
            raise RenderError(f"Invalid render report: {report}") from exc
        if recorded not in ("scene.json", "rendered-scene.json"):
            raise RenderError(f"Unexpected scene file in {report}")
        scene_name = recorded
    lesson, _checks = load_scene(directory / scene_name)
    try:
        streams = probe(executable("ffprobe"), video)["streams"]
        stream = next(stream for stream in streams if stream["codec_type"] == "video")
        duration = float(stream["duration"])
    except (KeyError, StopIteration, ValueError, subprocess.CalledProcessError) as exc:
        raise RenderError(f"Could not read the duration of {video}") from exc
    if abs(duration - lesson["duration"]) > .002:
        raise RenderError("The saved scene times do not match lesson.mp4. Use the scene from the video render.")
    destination = directory / "player.html"
    write_video_player(lesson, destination)
    print(f"Video player: {destination}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="stickman-lecture", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    diagnostic = commands.add_parser("doctor", help="check Node, Chromium and optional video dependencies")
    diagnostic.add_argument("--video", action="store_true", help="require video dependencies")
    diagnostic.add_argument("--narration", action="store_true", help="check the offline speech model")
    commands.add_parser("voice-setup", help="download the pinned offline speech model")
    validation = commands.add_parser("validate", help="verify schema, timeline and math assertions")
    validation.add_argument("scene", type=Path)
    navigation = commands.add_parser("player", help="create a chapter player for an already rendered MP4")
    navigation.add_argument("directory", type=Path, help="folder containing lesson.mp4 and the rendered scene")
    rendering = commands.add_parser("render", help="render a lesson from scene.json")
    rendering.add_argument("scene", type=Path)
    rendering.add_argument("--out", type=Path)
    rendering.add_argument("--mode", default="video", choices=["video", "web", "both"])
    rendering.add_argument("--preview", action="store_true", help="halve the video resolution while retaining the frame rate")
    rendering.add_argument("--audio", type=Path, help="optional local audio file to mix into video")
    rendering.add_argument("--narration", action="store_true", help="read the speech bubbles aloud")
    rendering.add_argument("--voice", default="F3", choices=VOICE_NAMES, help="preset voice for narration")
    rendering.add_argument("--no-bubble-sound", action="store_true", help="omit the sound at speech bubble changes")
    rendering.add_argument("--no-effects", action="store_true", help="omit all generated sound effects")
    rendering.add_argument("--fixed-timing", action="store_true", help="use the original scene times")
    args = parser.parse_args(argv)
    if getattr(args, "audio", None):
        if args.mode == "web" or not args.audio.is_file():
            parser.error("--audio requires video output and a local audio file")
        args.audio = args.audio.resolve()
    try:
        return {"doctor": doctor, "validate": validate, "render": render, "player": player,
                "voice-setup": voice_setup}[args.command](args)
    except (SceneError, RenderError, NarrationError, OSError) as exc:
        print(f"stickman-lecture: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
