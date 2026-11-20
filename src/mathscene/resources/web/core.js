(() => {
  const palette = {
    blue: "#83A9FF", amber: "#FFD18A", teal: "#72DFCA", rose: "#FF9FB2",
    white: "#F5F7FF", muted: "#A4B2CC", grid: "#334564", ink: "#111C31",
    background: "#0C1425", panel: "#121F36",
  };
  const font = '"Apple SD Gothic Neo", "Noto Sans CJK KR", "Malgun Gothic", sans-serif';
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  function evaluate(expr, variables) {
    if (!Array.isArray(expr)) {
      return typeof expr === "string" && Object.hasOwn(variables, expr) ? variables[expr] : expr;
    }
    const [name, ...args] = expr;
    if (name === "select") return evaluate(evaluate(args[0], variables) ? args[1] : args[2], variables);
    const values = args.map(value => evaluate(value, variables));
    const [a, b] = values;
    switch (name) {
      case "concat": return values.join("");
      case "add": return values.reduce((sum, value) => sum + value, 0);
      case "sub": return a - b;
      case "mul": return values.reduce((result, value) => result * value, 1);
      case "div": return a / b;
      case "max": return Math.max(...values);
      case "pow": return a ** b;
      case "sqrt": return Math.sqrt(a);
      case "exp": return Math.exp(a);
      case "lt": return a < b;
      case "round": {
        const scale = 10 ** (b ?? 0);
        return Math.round(a * scale) / scale;
      }
      default: throw Error("Unknown operation: " + name);
    }
  }

  function blendWeights(from, to, amount) {
    const weights = {};
    for (const [pose, weight] of Object.entries(from)) weights[pose] = weight * (1 - amount);
    weights[to] = (weights[to] ?? 0) + amount;
    return weights;
  }

  function weightsAt(gesture, time) {
    const u = clamp((time - gesture.at) / .32, 0, 1);
    return blendWeights(gesture.from, gesture.to, u * u * (3 - 2 * u));
  }

  function state(lesson, time, controls = {}) {
    const fps = lesson.canvas.fps;
    const frame = clamp(Math.floor(time * fps + 1e-7), 0, Math.round(lesson.duration * fps) - 1);
    const index = lesson.scenes.findLastIndex(scene => Math.round(scene.start * fps) <= frame);
    const scene = lesson.scenes[index];
    const local = Math.min(time, lesson.duration) - scene.start;
    const values = Object.fromEntries((scene.interactions ?? []).map(control =>
      [control.id, Object.hasOwn(controls, control.id) ? controls[control.id] : control.default]));
    const hidden = new Set(scene.events.filter(event => event.action === "show").map(event => event.target));
    const gestures = new Map();
    for (const event of scene.events) {
      if (event.at > local + 1e-7) break;
      if (event.action === "show") hidden.delete(event.target);
      if (event.action === "hide") hidden.add(event.target);
      if (event.action === "gesture") {
        const previous = gestures.get(event.target);
        const initial = scene.layers.find(layer => layer.id === event.target).pose;
        gestures.set(event.target, {
          at: event.at, to: event.value,
          from: previous ? weightsAt(previous, event.at) : {[initial]: 1},
        });
      }
    }
    const layers = scene.layers.filter(layer => !hidden.has(layer.id)).map(layer => {
      const resolved = {...layer};
      for (const [field, expr] of Object.entries(layer.bind ?? {})) {
        const value = evaluate(expr, values);
        if (typeof layer[field] !== typeof value || (typeof value === "number" && !Number.isFinite(value))) {
          throw Error(scene.id + "/" + layer.id + " invalid binding for " + field);
        }
        resolved[field] = value;
      }
      if (layer.type === "stick") {
        const gesture = gestures.get(layer.id);
        resolved.weights = gesture ? weightsAt(gesture, local) : {[layer.pose]: 1};
      }
      return resolved;
    });
    return {scene, index, local, values, layers};
  }

  function gaussianPoints(layer) {
    const {x, y, w, h, min, max, mean, sigma} = layer;
    return Array.from({length: 129}, (_, i) => {
      const fraction = i / 128;
      const z = (min + fraction * (max - min) - mean) / sigma;
      return [x + fraction * w, y + h - h * Math.exp(-0.5 * z * z) / sigma];
    });
  }

  function arrowPoints({x1, y1, x2, y2}, width) {
    const distance = Math.hypot(x2 - x1, y2 - y1);
    if (distance < .01) return [];
    const ux = (x2 - x1) / distance;
    const uy = (y2 - y1) / distance;
    const length = Math.min(12 + width * 1.2, distance * .45);
    const half = length * .48;
    const baseX = x2 - length * ux;
    const baseY = y2 - length * uy;
    return [[x2, y2], [baseX - uy * half, baseY + ux * half], [baseX + uy * half, baseY - ux * half]];
  }
  globalThis.MathScene = {palette, font, clamp, evaluate, state, gaussianPoints, arrowPoints};
})();
