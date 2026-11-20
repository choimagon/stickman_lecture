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

export function paceLesson(lesson) {
  const {fps} = lesson.canvas;
  const frame = seconds => Math.round(seconds * fps);
  let lessonEnd = 0;
  const scenes = lesson.scenes.map(scene => {
    const end = frame(scene.duration);
    const speakers = new Set(scene.layers.filter(layer => layer.type === "stick").map(layer => layer.id));
    const candidateFrames = [0, ...scene.events.filter(event => speakers.has(event.target) &&
      ["show", "hide", "speak"].includes(event.action)).map(event => frame(event.at))];
    let preceding;
    const speechFrames = [...new Set(candidateFrames)].flatMap(at => {
      const bubbles = visibleBubbles(MathScene.state(lesson, scene.start + at / fps));
      const key = JSON.stringify(bubbles);
      if (key === preceding) return [];
      preceding = key;
      return [{at, reading: readingFrames(bubbles, fps)}];
    });
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
