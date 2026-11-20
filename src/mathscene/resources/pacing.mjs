import "./web/core.js";

export function visibleBubbles(layerState) {
  return Object.fromEntries(layerState.layers.filter(layer => layer.type === "stick" && layer.bubble)
    .map(layer => [layer.id, layer.bubble]));
}

function readingFrames(bubbles, fps) {
  const letters = Object.values(bubbles).reduce((total, text) =>
    total + Array.from(text.normalize("NFC").replace(/\s/gu, "")).length, 0);
  return letters ? Math.ceil(Math.max(1.6, .85 + .145 * letters) * fps) : 0;
}

function sceneSpeech(lesson, scene) {
  const {fps} = lesson.canvas;
  const speakers = new Set(scene.layers.filter(layer => layer.type === "stick").map(layer => layer.id));
  const candidates = [0, ...scene.events.filter(event => speakers.has(event.target) &&
    ["show", "hide", "speak"].includes(event.action)).map(event => Math.round(event.at * fps))];
  let preceding;
  return [...new Set(candidates)].flatMap(at => {
    const bubbles = visibleBubbles(MathScene.state(lesson, scene.start + at / fps));
    const key = JSON.stringify(bubbles);
    if (key === preceding) return [];
    preceding = key;
    return [{at, bubbles, text: Object.values(bubbles).join(" ").trim()}];
  });
}

export function speechSpans(lesson) {
  const {fps} = lesson.canvas;
  const spans = [];
  for (const scene of lesson.scenes) {
    const from = Math.round(scene.start * fps);
    const points = sceneSpeech(lesson, scene);
    points.forEach(({at, text}, i) => {
      if (!text) return;
      const to = from + (points[i + 1]?.at ?? Math.round(scene.duration * fps));
      const previous = spans.at(-1);
      if (previous && previous.end === from + at && previous.text === text) previous.end = to;
      else spans.push({start: from + at, end: to, text});
    });
  }
  return spans;
}

export function paceLesson(lesson, minimums = {}) {
  const {fps} = lesson.canvas;
  const frame = seconds => Math.round(seconds * fps);
  let lessonEnd = 0;
  const scenes = lesson.scenes.map(scene => {
    const end = frame(scene.duration);
    const speechFrames = sceneSpeech(lesson, scene).map(({at, bubbles, text}) => ({
      at, reading: Math.max(readingFrames(bubbles, fps),
        Object.hasOwn(minimums, text) ? Math.ceil(minimums[text] * fps) : 0),
    }));
    const visualEnds = scene.events.filter(event => event.action !== "speak").map(event => {
      const at = frame(event.at);
      const duration = event.action === "draw" ? frame(event.duration) :
        event.action === "gesture" ? Math.ceil(.32 * fps) : 0;
      return {at, end: at + duration};
    });
    for (const track of scene.tracks ?? []) {
      track.keyframes.forEach((key, i) => {
        const previous = track.keyframes[i - 1];
        const at = frame(key.at);
        if (previous && previous.value !== key.value) {
          visualEnds.push({at: frame(previous.at), end: at});
        } else if (at < end) {
          visualEnds.push({at, end: at});
        }
      });
    }
    let sceneEnd = 0;
    const spans = speechFrames.map(({at, reading}, i) => {
      const next = speechFrames[i + 1]?.at ?? end;
      let protectedEnd = at + 1;
      for (const visual of visualEnds) {
        if (visual.at < next && visual.end >= at) {
          protectedEnd = Math.max(protectedEnd, Math.min(next, visual.end + Math.ceil(.55 * fps)));
        }
      }
      const duration = reading ? Math.max(reading, protectedEnd - at) : next - at;
      const span = {at, shift: sceneEnd - at};
      sceneEnd += duration;
      return span;
    });
    function remap(seconds) {
      const at = frame(seconds);
      if (at === end) return sceneEnd / fps;
      const {shift} = spans.findLast(span => span.at <= at);
      return (at + shift) / fps;
    }
    const events = scene.events.map(event => ({...event, at: remap(event.at)}));
    const paced = {...scene, events, start: lessonEnd / fps, duration: sceneEnd / fps};
    if (scene.tracks) {
      paced.tracks = scene.tracks.map(track => ({...track, keyframes: track.keyframes.map(key => ({
        ...key, at: remap(key.at),
      }))}));
    }
    lessonEnd += sceneEnd;
    return paced;
  });
  return {...lesson, scenes, duration: lessonEnd / fps};
}
