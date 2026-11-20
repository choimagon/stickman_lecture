(() => {
  const lesson = globalThis.MATHSCENE_LESSON;
  const {palette, state, clamp, gaussianPoints, arrowPoints} = MathScene;
  const byId = id => document.getElementById(id);
  const ui = Object.fromEntries(["title", "stage", "scene-title", "stage-count", "math", "stick", "play",
    "prev", "next", "seek", "clock", "stage-description", "sliders", "steps", "definitions"].map(id => [id, byId(id)]));
  const {width, height, fps} = lesson.canvas;
  const svgNS = "http://www.w3.org/2000/svg";
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  let time = 0;
  let previous = null;
  let current;
  let running = false;
  let animation = 0;
  let overlay;
  const controls = new Map();

  function svg(tag, attributes) {
    const node = document.createElementNS(svgNS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function mathLayer(layer) {
    const color = palette[layer.color ?? "white"];
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
    if (layer.type === "rect") return svg("rect", {x, y, width: layer.w, height: layer.h, rx: 5, fill, stroke: color, "stroke-width": w});
    if (layer.type === "gaussian") return svg("polyline", {points: gaussianPoints(layer).join(" "),
      fill: "none", stroke: color, "stroke-width": w, "stroke-linejoin": "round"});
    const {x1, y1, x2, y2} = layer;
    const line = svg("line", {x1, y1, x2, y2, stroke: color, "stroke-linecap": "round", "stroke-width": w});
    if (layer.type === "line") return line;
    const group = svg("g", {});
    group.append(line);
    const arrow = arrowPoints(layer, w);
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
        value: values[control.id] ?? control.default});
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

  function render(forceMath = false) {
    const sceneAtTime = state(lesson, time);
    current = state(lesson, time, controls.get(sceneAtTime.scene.id));
    const {scene, index} = current;
    if (previous !== index) {
      previous = index;
      ui["scene-title"].textContent = scene.title;
      ui["stage-count"].textContent = (index + 1) + " / " + lesson.scenes.length;
      ui["stage-description"].textContent = scene.narration;
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
      ui.math.replaceChildren(...layers.map(layer => {
        const element = mathLayer(layer);
        element.dataset.layer = layer.id;
        element.dataset.type = layer.type;
        return element;
      }));
      ui.math.dataset.key = key;
    }
    overlay = MathSceneStick.draw(ui.stick, lesson, current, {captions: false, motion: !motion.matches});
    ui.seek.value = Math.round(time * fps);
    ui.clock.value = time.toFixed(1) + " / " + lesson.duration.toFixed(1) + "초";
  }

  function seek(seconds) {
    time = clamp(seconds, 0, lesson.duration);
    render();
  }
  function playback(value) {
    running = value;
    ui.play.textContent = running ? "일시정지" : "재생";
    cancelAnimationFrame(animation);
    if (!running) return;
    if (time >= lesson.duration) seek(0);
    let prior = performance.now();
    const tick = now => {
      seek(time + Math.max(0, (now - prior) / 1000));
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
  document.title = lesson.title + " · MathScene";
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
  motion.addEventListener("change", () => render());
  render();
  globalThis.mathscenePlayer = {seek, get state() { return current; }, get overlay() { return overlay; }};
})();
