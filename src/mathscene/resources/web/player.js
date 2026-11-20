(() => {
  const lesson = globalThis.MATHSCENE_LESSON;
  const {paletteFor, state, clamp, geometry, speech} = MathScene;
  const palette = paletteFor(lesson.theme);
  const byId = id => document.getElementById(id);
  const ui = Object.fromEntries(["title", "stage", "scene-title", "stage-count", "math", "stick", "play",
    "prev", "next", "seek", "clock", "stage-description", "sliders", "steps", "definitions"].map(id => [id, byId(id)]));
  const {width, height, fps} = lesson.canvas;
  const svgNS = "http://www.w3.org/2000/svg";
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  const compact = matchMedia("(max-width: 760px)");
  let time = 0;
  let previous = null;
  let current;
  let running = false;
  let animation = 0;
  let playRequest = 0;
  let audioFailed = false;
  let overlay;
  const controls = new Map();
  const audio = globalThis.MATHSCENE_NARRATION ? byId("narration") : null;
  const voiceToggle = byId("voice-toggle");

  function disableVoice() {
    audioFailed = true;
    voiceToggle.disabled = true;
    voiceToggle.setAttribute("aria-pressed", "false");
  }

  if (audio) {
    voiceToggle.hidden = false;
    audio.addEventListener("error", disableVoice);
    audio.src = "narration.wav";
    voiceToggle.onclick = () => {
      audio.muted = !audio.muted;
      voiceToggle.setAttribute("aria-pressed", String(!audio.muted));
    };
  }

  function svg(tag, attributes) {
    const node = document.createElementNS(svgNS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function mathLayer(layer) {
    const color = palette[layer.color ?? "foreground"];
    const fill = layer.fill ? palette[layer.fill] : "none";
    const w = layer.width ?? 2.5;
    const size = layer.size ?? 32;
    const {x, y} = layer;
    const anchor = {left: "start", center: "middle", right: "end"}[layer.align ?? "left"];
    if (layer.type === "text") {
      const element = svg("text", {x, y, "font-size": size, "text-anchor": anchor, "dominant-baseline": "central", fill: color});
      element.textContent = layer.text;
      return element;
    }
    if (layer.type === "formula") {
      const x0 = anchor === "start" ? x : anchor === "middle" ? 0 : 2 * x - width;
      const fw = anchor === "middle" ? 2 * x : width - x0;
      const element = svg("foreignObject", {x: x0, y: y - 75, width: Math.max(1, fw), height: 150, overflow: "visible"});
      const box = document.createElement("div");
      box.className = "formula-box";
      box.style.cssText = "font-size:" + size + "px;color:" + color;
      box.style.justifyContent = {start: "flex-start", middle: "center", end: "flex-end"}[anchor];
      const span = document.createElement("span");
      katex.render(layer.tex, span, {throwOnError: true, trust: false, displayMode: false});
      box.append(span);
      element.append(box);
      return element;
    }
    if (layer.type === "circle") return svg("circle", {cx: x, cy: y, r: layer.r, fill, stroke: color, "stroke-width": w});
    if (layer.type === "ellipse") return svg("ellipse", {cx: x, cy: y, rx: layer.rx, ry: layer.ry, fill, stroke: color, "stroke-width": w});
    if (layer.type === "rect") return svg("rect", {x, y, width: layer.w, height: layer.h, fill, stroke: color, "stroke-width": w});
    if (layer.type === "polygon") return svg("polygon", {points: layer.points.join(" "), fill,
      stroke: color, "stroke-width": w, "stroke-linejoin": "round"});
    if (layer.type === "gaussian" || layer.type === "polyline") return svg("polyline", {points: layer.points.join(" "),
      fill: "none", stroke: color, "stroke-width": w, "stroke-linejoin": "round"});
    const {x1, y1, x2, y2} = layer;
    const line = svg("line", {x1, y1, x2, y2, stroke: color, "stroke-linecap": "round", "stroke-width": w});
    if (layer.type === "line") return line;
    const group = svg("g", {});
    group.append(line);
    const arrow = layer.arrow;
    if (arrow.length) group.append(svg("polygon", {points: arrow.join(" "), fill: color}));
    return group;
  }

  function sliderList(scene) {
    ui.sliders.replaceChildren();
    const items = scene.interactions ?? [];
    ui.sliders.hidden = items.length === 0;
    if (!controls.has(scene.id)) controls.set(scene.id, Object.create(null));
    const values = controls.get(scene.id);
    for (const control of items) {
      const wrapper = document.createElement("div");
      wrapper.className = "slider";
      const label = document.createElement("label");
      const id = "control-" + control.id;
      label.htmlFor = id;
      label.textContent = control.label;
      const input = document.createElement("input");
      Object.assign(input, {type: "range", id, min: control.min, max: control.max, step: control.step,
        value: current.values[control.id]});
      const output = document.createElement("output");
      output.htmlFor = id;
      output.value = input.value;
      input.addEventListener("input", () => {
        values[control.id] = Number(input.value);
        output.value = input.value;
        render(true);
      });
      wrapper.append(label, input, output);
      ui.sliders.append(wrapper);
    }
  }

  function mathElement(layer) {
    const drawn = geometry(layer, {complete: motion.matches});
    const element = drawn ? mathLayer(drawn) : svg("g", {});
    element.dataset.layer = layer.id;
    element.dataset.type = layer.type;
    element.dataset.progress = motion.matches ? 1 : layer.progress ?? 1;
    element.dataset.visual = visualKey(layer);
    if (!drawn) element.setAttribute("visibility", "hidden");
    return element;
  }

  function visualKey(layer) {
    const progress = motion.matches ? 1 : layer.progress ?? 1;
    return JSON.stringify([progress, ...Object.keys(layer.bind ?? {}).map(field => layer[field])]);
  }

  function render(forceMath = false) {
    const sceneAtTime = state(lesson, time);
    current = state(lesson, time, controls.get(sceneAtTime.scene.id), {reduceMotion: motion.matches});
    const {scene, index} = current;
    if (previous !== index) {
      previous = index;
      ui["scene-title"].textContent = scene.title;
      ui["stage-count"].textContent = (index + 1) + " / " + lesson.scenes.length;
      ui.prev.disabled = index === 0;
      ui.next.disabled = index + 1 === lesson.scenes.length;
      ui.steps.querySelectorAll("button").forEach((button, i) => {
        if (i === index) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });
      sliderList(scene);
      forceMath = true;
    }
    const layers = current.layers.filter(layer => layer.type !== "stick");
    const key = layers.map(layer => layer.id).join("|");
    if (forceMath || ui.math.dataset.key !== key) {
      ui.math.replaceChildren(...layers.map(mathElement));
      ui.math.dataset.key = key;
    } else {
      layers.forEach((layer, i) => {
        const element = ui.math.children[i];
        if (element.dataset.visual !== visualKey(layer)) {
          element.replaceWith(mathElement(layer));
        }
      });
    }
    const overrides = controls.get(scene.id);
    for (const control of scene.interactions ?? []) {
      if (Object.hasOwn(overrides, control.id)) continue;
      const slider = byId("control-" + control.id);
      slider.value = current.values[control.id];
      slider.nextElementSibling.value = slider.value;
    }
    const spoken = speech(current);
    if (ui["stage-description"].textContent !== spoken) ui["stage-description"].textContent = spoken;
    overlay = MathSceneStick.draw(ui.stick, lesson, current, {speech: !compact.matches, motion: !motion.matches});
    ui.seek.value = Math.round(time * fps);
    ui.clock.value = time.toFixed(1) + " / " + lesson.duration.toFixed(1) + "초";
  }

  function seek(seconds, syncAudio = true) {
    time = clamp(seconds, 0, lesson.duration);
    if (syncAudio && audio && !audioFailed) audio.currentTime = time;
    render();
  }
  function playback(value) {
    const request = ++playRequest;
    running = value;
    ui.play.textContent = running ? "일시정지" : "재생";
    cancelAnimationFrame(animation);
    if (!running) {
      audio?.pause();
      return;
    }
    if (time >= lesson.duration) seek(0);
    if (audio && !audioFailed) {
      audio.currentTime = time;
      audio.play().catch(() => {
        if (request === playRequest && running) disableVoice();
      });
    }
    let prior = performance.now();
    const tick = now => {
      const nextTime = audio && !audioFailed && !audio.ended
        ? audio.currentTime
        : time + Math.max(0, (now - prior) / 1000);
      seek(nextTime, false);
      prior = now;
      if (time >= lesson.duration) playback(false);
      else if (running) animation = requestAnimationFrame(tick);
    };
    animation = requestAnimationFrame(tick);
  }

  const go = index => {
    playback(false);
    seek(lesson.scenes[clamp(index, 0, lesson.scenes.length - 1)].start);
  };

  document.documentElement.lang = lesson.locale;
  document.documentElement.dataset.theme = lesson.theme;
  const brand = /^ko(?:-|$)/i.test(lesson.locale) ? "졸라맨 강의" : "StickMan Lecture";
  byId("brand").textContent = brand;
  document.title = lesson.title + " · " + brand;
  ui.title.textContent = lesson.title;
  ui.stage.style.aspectRatio = width + " / " + height;
  ui.math.setAttribute("viewBox", [0, 0, width, height].join(" "));
  ui.stick.width = width;
  ui.stick.height = height;
  ui.seek.max = Math.round(lesson.duration * fps);
  ui.play.onclick = () => playback(!running);
  ui.prev.onclick = () => go(current.index - 1);
  ui.next.onclick = () => go(current.index + 1);
  ui.seek.oninput = () => seek(Number(ui.seek.value) / fps);
  lesson.scenes.forEach((scene, i) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    const number = document.createElement("span");
    number.textContent = String(i + 1).padStart(2, "0");
    button.append(number, document.createTextNode(scene.title));
    button.onclick = () => go(i);
    li.append(button);
    ui.steps.append(li);
  });
  ui.definitions.hidden = !lesson.definitions.length;
  const list = ui.definitions.querySelector("dl");
  for (const {symbol, meaning} of lesson.definitions) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = symbol;
    dd.textContent = meaning;
    list.append(dt, dd);
  }
  document.addEventListener("keydown", event => {
    if (event.altKey || event.ctrlKey || event.metaKey ||
        event.target.closest("input, button, summary, a, textarea, select")) return;
    if (event.code === "Space") {
      event.preventDefault();
      playback(!running);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      go(current.index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      go(current.index - 1);
    }
  });
  motion.addEventListener("change", () => render(true));
  compact.addEventListener("change", () => render());
  render();
  globalThis.mathscenePlayer = {seek, get state() { return current; }, get overlay() { return overlay; }};
})();
