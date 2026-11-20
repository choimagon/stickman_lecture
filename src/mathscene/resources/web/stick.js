(() => {
  const {paletteFor, font} = MathScene;
  const rig = window.RIG;
  const poses = {
    idle: rig.BASE,
    point_right: rig.P({hF: [38, -97], head: [3, -116]}),
    explain: rig.P({hF: [33, -88], hB: [-24, -87], hang: 0}),
    wave: rig.BASE,
  };

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

  function actorPose(layer, time, scale) {
    let pose = rig.BASE;
    let mass = 0;
    for (const [name, weight] of Object.entries(layer.weights)) {
      if (!weight) continue;
      mass += weight;
      pose = rig.mix(pose, poses[name], weight / mass);
    }
    pose = rig.breathe(pose, time);
    if (layer.walk) {
      const {distance, speed} = layer.walk;
      const phase = distance / (rig.STRIDE * 2 * scale);
      pose = rig.legs(pose, phase, rig.clamp(Math.abs(speed) / 20, 0, 1), {arms: !layer.contact});
    }
    if (layer.contact) {
      const {x, y, grip} = layer.contact;
      pose = rig.shift(pose, 4 * grip, 0, ["head", "chest"]);
      const hand = [(x - layer.x) / scale, (y - layer.y) / scale];
      pose = rig.P({hF: rig.L2(pose.hF, hand, grip)}, pose);
    }
    return pose;
  }

  function figure(ctx, layer, time, palette, speech) {
    const {x, y, scale = 1, weights, bubble} = layer;
    const rigScale = scale * 1.25;
    const pose = actorPose(layer, time, rigScale);
    const drawing = rig.fig(ctx, pose, x, y, {s: rigScale,
      wave: (weights.wave ?? 0) * (1 - (layer.contact?.grip ?? 0)), wt: time,
      ink: palette.ground ? undefined : palette.white, far: palette.ground ? undefined : palette.muted});
    const w = drawing.w;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(scale, scale);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
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
    const contact = layer.contact?.grip >= .995 ?
      Math.hypot(w.handF[0] - layer.contact.x, w.handF[1] - layer.contact.y) : null;
    return {id: layer.id, joints: [w.head, w.sh, w.eB, w.handB, w.eF, w.handF, w.fF, w.fB],
      feet: [w.fF, w.fB], bubble: bubbleRect, contact,
      walking: Boolean(layer.walk && Math.abs(layer.walk.speed) > .1)};
  }

  function ground(ctx, {width, height}, palette) {
    const y = height * .894;
    ctx.fillStyle = palette.ground;
    ctx.fillRect(0, y, width, height - y);
    const points = Array.from({length: Math.ceil(width / 7) + 1},
      (_, i) => [Math.min(width, i * 7), y + .49 * Math.sin(i * .39) + .21 * Math.cos(i * 1.14)]);
    rig.strokePath(ctx, points, 1.4, palette.figure);
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
