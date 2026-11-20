(() => {
  const {palette, font} = MathScene;
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
      if (row && ctx.measureText(row + " " + word).width > width) {
        rows.push(row);
        row = "";
      }
      for (const char of word) {
        if (row && ctx.measureText(row + char).width > width) {
          rows.push(row);
          row = "";
        }
        row += char;
      }
      row += " ";
    }
    if (row.trim()) rows.push(row.trim());
    return rows;
  }

  function figure(ctx, layer, time) {
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
    ctx.strokeStyle = palette.blue;
    ctx.fillStyle = palette.panel;
    ctx.beginPath();
    ctx.ellipse(0, 5, 57, 11, 0, 0, Math.PI * 2);
    ctx.fill();
    line(ctx, [[-37, 0], ...anchors, [39, 0]]);
    ctx.strokeStyle = palette.white;
    line(ctx, [[sway, -50], [-16, -25], anchors[0]]);
    line(ctx, [[sway, -50], [17, -25], anchors[1]]);
    line(ctx, [[sway, -116], [sway, -50]]);
    ctx.lineWidth = 4.5;
    line(ctx, [[sway, -96], el, hl]);
    line(ctx, [[sway, -96], er, hr]);
    ctx.beginPath();
    ctx.arc(sway + 1, -136, 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.strokeStyle = palette.teal;
    ctx.lineWidth = 3.5;
    line(ctx, [[sway + 5, -137], [sway + 6, -137]]);
    line(ctx, [[sway + 11, -130], [sway + 15, -132]]);
    let bubbleRect = null;
    if (bubble) {
      ctx.font = "600 19px " + font;
      const rows = wrap(ctx, bubble, 205);
      const width = Math.max(100, ...rows.map(row => ctx.measureText(row).width + 26));
      const height = rows.length * 24 + 18;
      const bx = -width / 2;
      const by = -190 - height;
      bubbleRect = {left: x + bx * scale, top: y + by * scale,
        right: x + (bx + width) * scale, bottom: y - 179 * scale};
      ctx.fillStyle = palette.panel;
      ctx.strokeStyle = palette.grid;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(bx, by, width, height, 12);
      ctx.fill();
      ctx.stroke();
      line(ctx, [[-10, by + height], [0, by + height + 10], [10, by + height]]);
      ctx.fillStyle = palette.teal;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      rows.forEach((row, i) => ctx.fillText(row, 0, by + 21 + i * 24));
    }
    ctx.restore();
    const point = ([dx, dy]) => [x + dx * scale, y + dy * scale];
    return {id: layer.id, joints: [[sway, -157], [sway, -96], ...arms, ...anchors].map(point),
      feet: anchors.map(point), bubble: bubbleRect};
  }

  function subtitle(ctx, lesson, scene) {
    const {width, height} = lesson.canvas;
    ctx.font = "600 24px " + font;
    const rows = wrap(ctx, scene.narration, width - 150);
    const block = 22 + rows.length * 29;
    const y = height - block - 24;
    ctx.fillStyle = palette.panel;
    ctx.strokeStyle = palette.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(38, y, width - 76, block, 12);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = palette.white;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    rows.forEach((row, i) => ctx.fillText(row, width / 2, y + 24 + i * 29));
    return {left: 38, right: width - 38, top: y, bottom: height - 24, lines: rows.length};
  }

  function draw(canvas, lesson, state, {captions = true, motion = true} = {}) {
    const ctx = canvas.getContext("2d");
    ctx.setTransform(canvas.width / lesson.canvas.width, 0, 0, canvas.height / lesson.canvas.height, 0, 0);
    ctx.clearRect(0, 0, lesson.canvas.width, lesson.canvas.height);
    const figures = state.layers.filter(layer => layer.type === "stick")
      .map(layer => figure(ctx, layer, motion ? state.local : 0));
    const caption = captions ? subtitle(ctx, lesson, state.scene) : null;
    return {figures, caption};
  }
  globalThis.MathSceneStick = {draw};
})();
