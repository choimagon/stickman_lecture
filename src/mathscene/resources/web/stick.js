(() => {
  const {paletteFor, font} = MathScene;
  const armPoses = {
    idle: [[-30, -72], [-32, -51], [30, -72], [32, -51]],
    point_right: [[-31, -71], [-24, -51], [38, -103], [73, -116]],
    explain: [[-38, -82], [-53, -100], [39, -83], [56, -100]],
    wave: [[-28, -72], [-30, -52], [36, -103], [32, -137]],
  };

  function line(ctx, points) {
    ctx.beginPath();
    points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.stroke();
  }

  function wrap(ctx, text, width) {
    const rows = [];
    let row = "";
    for (const word of text.split(/\s+/)) {
      if (row && ctx.measureText(row + word).width > width) {
        rows.push(row.trim());
        row = "";
      }
      for (const char of word) {
        if (row && ctx.measureText(row + char).width > width) {
          rows.push(row.trim());
          row = "";
        }
        row += char;
      }
      row += " ";
    }
    if (row.trim()) rows.push(row.trim());
    return rows;
  }

  function figure(ctx, layer, time, palette, speech) {
    const {x, y, scale = 1, weights, bubble} = layer;
    const sway = Math.sin(time * 2.1) * 2;
    const wave = Math.sin(time * 8) * 5 * (weights.wave ?? 0);
    const arms = armPoses.idle.map((_, i) => Object.entries(weights).reduce(([px, py], [pose, weight]) => {
      const [ax, ay] = armPoses[pose][i];
      return [px + ax * weight, py + ay * weight];
    }, [0, 0]));
    arms[3][0] += wave;
    const [el, hl, er, hr] = arms;
    const anchors = [[-26, 0], [28, 0]];
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(scale, scale);
    ctx.lineWidth = 5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = palette.figure ?? palette.blue;
    ctx.fillStyle = palette.ground ?? palette.panel;
    ctx.beginPath();
    ctx.ellipse(0, 5, 57, 11, 0, 0, Math.PI * 2);
    ctx.fill();
    line(ctx, [[-37, 0], ...anchors, [39, 0]]);
    ctx.strokeStyle = palette.figure ?? palette.white;
    line(ctx, [[sway, -50], [-16, -25], anchors[0]]);
    line(ctx, [[sway, -50], [17, -25], anchors[1]]);
    line(ctx, [[sway, -116], [sway, -50]]);
    ctx.lineWidth = 4.5;
    line(ctx, [[sway, -96], el, hl]);
    line(ctx, [[sway, -96], er, hr]);
    ctx.beginPath();
    ctx.arc(sway + 1, -136, 20, 0, Math.PI * 2);
    ctx.fillStyle = palette.background;
    ctx.fill();
    ctx.stroke();
    ctx.strokeStyle = palette.figure ?? palette.teal;
    ctx.lineWidth = 3.5;
    line(ctx, [[sway + 5, -137], [sway + 6, -137]]);
    line(ctx, [[sway + 11, -130], [sway + 15, -132]]);
    let bubbleRect = null;
    if (speech && bubble) {
      ctx.font = "600 22px " + font;
      const rows = wrap(ctx, bubble, 278);
      const width = Math.max(104, ...rows.map(row => ctx.measureText(row).width + 38));
      const height = rows.length * 29 + 22;
      const bx = -width / 2;
      const by = -188 - height;
      bubbleRect = {left: x + bx * scale, top: y + by * scale,
        right: x + (bx + width) * scale, bottom: y - 173 * scale};
      ctx.fillStyle = palette.panel;
      ctx.strokeStyle = palette.figure ?? palette.grid;
      ctx.lineWidth = 1.9;
      ctx.beginPath();
      const bottom = by + height;
      ctx.moveTo(bx + 17, by);
      ctx.arcTo(bx + width, by, bx + width, bottom, 17);
      ctx.arcTo(bx + width, bottom, 15, bottom, 17);
      ctx.lineTo(15, bottom);
      ctx.lineTo(-2, bottom + 14);
      ctx.lineTo(-3, bottom);
      ctx.arcTo(bx, bottom, bx, by, 17);
      ctx.arcTo(bx, by, bx + 17, by, 17);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = palette.white;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      rows.forEach((row, i) => ctx.fillText(row, 0, by + 26 + i * 29));
    }
    ctx.restore();
    const point = ([dx, dy]) => [x + dx * scale, y + dy * scale];
    return {id: layer.id, joints: [[sway, -157], [sway, -96], ...arms, ...anchors].map(point),
      feet: anchors.map(point), bubble: bubbleRect};
  }

  function ground(ctx, {width, height}, palette) {
    const y = height * .894;
    ctx.fillStyle = palette.ground;
    ctx.fillRect(0, y, width, height - y);
    ctx.strokeStyle = palette.figure;
    ctx.lineWidth = 1.65;
    const points = Array.from({length: Math.ceil(width / 7) + 1},
      (_, i) => [Math.min(width, i * 7), y + .49 * Math.sin(i * .39) + .21 * Math.cos(i * 1.14)]);
    line(ctx, points);
  }

  function draw(canvas, lesson, state, {speech = true, motion = true} = {}) {
    const ctx = canvas.getContext("2d");
    ctx.setTransform(canvas.width / lesson.canvas.width, 0, 0, canvas.height / lesson.canvas.height, 0, 0);
    ctx.clearRect(0, 0, lesson.canvas.width, lesson.canvas.height);
    const palette = paletteFor(lesson.theme);
    if (palette.ground) ground(ctx, lesson.canvas, palette);
    const figures = state.layers.filter(layer => layer.type === "stick")
      .map(layer => figure(ctx, layer, motion ? state.local : 0, palette, speech));
    return {figures};
  }
  globalThis.MathSceneStick = {draw};
})();
