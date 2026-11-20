import {createRequire} from "node:module";
import {createServer} from "node:http";
import {spawn} from "node:child_process";
import {once} from "node:events";
import {readFile, writeFile, mkdir} from "node:fs/promises";
import {dirname, extname, join, resolve, sep} from "node:path";
import {fileURLToPath, pathToFileURL} from "node:url";
import "./web/core.js";

const [command, dependencyDir, ...args] = process.argv.slice(2);
const require = createRequire(join(dependencyDir, "package.json"));
const resources = dirname(fileURLToPath(import.meta.url));
const {palette, state, gaussianPoints, arrowPoints} = MathScene;

async function prepare(sceneFile, work) {
  const {mathjax} = require("mathjax-full/js/mathjax.js");
  const {TeX} = require("mathjax-full/js/input/tex.js");
  const {SVG} = require("mathjax-full/js/output/svg.js");
  const {liteAdaptor} = require("mathjax-full/js/adaptors/liteAdaptor.js");
  const {RegisterHTMLHandler} = require("mathjax-full/js/handlers/html.js");
  require("mathjax-full/js/input/tex/ams/AmsConfiguration.js");
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({packages: ["base", "ams"], formatError: (_jax, error) => { throw error; }});
  const mj = mathjax.document("", {InputJax: tex, OutputJax: new SVG({fontCache: "none"})});
  const lesson = JSON.parse(await readFile(sceneFile, "utf8"));
  const {fps} = lesson.canvas;
  const formulas = new Map();
  const segments = [];
  for (const scene of lesson.scenes) {
    const points = [...new Set([0, ...scene.events.map(e => Math.round(e.at * fps)), Math.round(scene.duration * fps)])];
    for (let i = 0; i < points.length - 1; i++) {
      const {index, layers} = state(lesson, scene.start + points[i] / fps);
      const math = [];
      for (const source of layers) {
        const layer = {...source};
        if (layer.type === "stick") continue;
        if (layer.type === "formula") {
          if (!formulas.has(layer.tex)) {
            const name = "formula-" + formulas.size + ".svg";
            const node = adaptor.firstChild(mj.convert(layer.tex, {display: false}));
            const svg = adaptor.outerHTML(node).replaceAll("currentColor", "#ffffff");
            await writeFile(join(work, name), svg);
            const view = adaptor.getAttribute(node, "viewBox").split(/ +/).map(Number);
            if (view.length !== 4 || !view.every(Number.isFinite)) throw Error("bad formula dimensions: " + layer.id);
            formulas.set(layer.tex, {file: name, heightEm: view[3] / 1000});
          }
          Object.assign(layer, formulas.get(layer.tex));
        }
        if (layer.type === "gaussian") layer.points = gaussianPoints(layer);
        if (layer.type === "vector") layer.arrow = arrowPoints(layer, layer.width ?? 2.5);
        math.push(layer);
      }
      segments.push({scene: index, frames: points[i + 1] - points[i], layers: math});
    }
  }
  await writeFile(join(work, "segments.json"), JSON.stringify({lesson, palette, segments}));
}

async function launch() {
  const {chromium} = require("playwright");
  const override = process.env.MATHSCENE_CHROMIUM;
  return chromium.launch(override ? {executablePath: override} : {});
}

function checkMotion(report, lesson, index, overlay, previous, fps) {
  const {width, height} = lesson.canvas;
  for (const figure of overlay.figures) {
    for (const [x, y] of figure.joints) {
      if (x < 4 || x > width - 4 || y < 116 || y > height - 4) {
        throw Error("stick joint outside safe stage in " + index + "/" + figure.id);
      }
    }
    if (figure.bubble && (figure.bubble.left < 4 || figure.bubble.right > width - 4 || figure.bubble.top < 116)) {
      throw Error("speech bubble outside safe stage in " + index + "/" + figure.id);
    }
    const before = previous?.index === index && previous.overlay.figures.find(f => f.id === figure.id);
    if (before) {
      const shift = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]);
      const joints = Math.max(...figure.joints.map((p, i) => shift(p, before.joints[i])));
      const feet = Math.max(...figure.feet.map((p, i) => shift(p, before.feet[i])));
      report.maxJointPixelsPerFrame = Math.max(report.maxJointPixelsPerFrame, joints);
      report.maxFootPixelsPerFrame = Math.max(report.maxFootPixelsPerFrame, feet);
      if (joints > 1600 / fps || feet > 75 / fps) {
        throw Error("abrupt joint motion or foot sliding in " + index + "/" + figure.id);
      }
    }
  }
  if (overlay.caption?.top < 120 || overlay.caption?.lines > 3) throw Error("caption is too long in scene " + index);
}

async function capture(sceneFile, work, w, h, ffmpeg) {
  const lesson = JSON.parse(await readFile(sceneFile, "utf8"));
  const {fps} = lesson.canvas;
  const count = Math.round(lesson.duration * fps);
  const browser = await launch();
  const report = {frames: count, maxJointPixelsPerFrame: 0, maxFootPixelsPerFrame: 0};
  let encoder;
  let encoderResult;
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(join(resources, "web", "capture.html")).href);
    await page.evaluate(({lesson, w, h}) => {
      globalThis.lessonForCapture = lesson;
      const canvas = document.getElementById("output");
      Object.assign(canvas, {width: w, height: h});
    }, {lesson, w: Number(w), h: Number(h)});
    encoder = spawn(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate",
      String(fps), "-vcodec", "png", "-i", "pipe:0", "-an", "-c:v", "qtrle", "-pix_fmt", "argb",
      join(work, "overlay.mov")], {stdio: ["pipe", "inherit", "inherit"]});
    encoder.stdin.on("error", () => {});
    encoderResult = once(encoder, "close");
    let previous;
    for (let start = 0; start < count; start += 12) {
      const batch = await page.evaluate(({start, stop, fps}) => {
        const frames = [];
        const canvas = document.getElementById("output");
        for (let frame = start; frame < stop; frame++) {
          const s = MathScene.state(lessonForCapture, frame / fps);
          const overlay = MathSceneStick.draw(canvas, lessonForCapture, s);
          frames.push({index: s.index, overlay, png: canvas.toDataURL("image/png").split(",")[1]});
        }
        return frames;
      }, {start, stop: Math.min(start + 12, count), fps});
      for (const frame of batch) {
        checkMotion(report, lesson, frame.index, frame.overlay, previous, fps);
        previous = {index: frame.index, overlay: frame.overlay};
        if (encoder.stdin.destroyed) throw Error("overlay encoder closed before all frames arrived");
        if (!encoder.stdin.write(Buffer.from(frame.png, "base64"))) {
          await new Promise((resolve, reject) => {
            const stream = encoder.stdin;
            function cleanup() {
              stream.off("drain", drain);
              stream.off("close", close);
            }
            function drain() { cleanup(); resolve(); }
            function close() { cleanup(); reject(Error("overlay encoder closed")); }
            stream.once("drain", drain);
            stream.once("close", close);
          });
        }
      }
    }
    encoder.stdin.end();
    const [code] = await encoderResult;
    if (code !== 0) throw Error("overlay encoder exited with status " + code);
    await writeFile(join(work, "motion.json"), JSON.stringify(report, null, 2));
  } finally {
    if (encoder && encoder.exitCode === null && encoder.signalCode === null) encoder.kill();
    await browser.close();
  }
}

async function serve(root) {
  const types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2"};
  const server = createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
      const file = resolve(root, "." + (pathname === "/" ? "/index.html" : pathname));
      if (!file.startsWith(root + sep)) throw Error("outside web directory");
      const body = await readFile(file);
      response.writeHead(200, {"Content-Type": types[extname(file)] ?? "application/octet-stream"});
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  return {server, url: "http://127.0.0.1:" + server.address().port + "/"};
}

async function verify(web, work, preview) {
  const {server, url} = await serve(resolve(web));
  let browser;
  const report = {viewports: [], samples: 0, controls: 0, overlapWarnings: []};
  try {
    browser = await launch();
    for (const viewport of [{width: 1440, height: 920}, {width: 390, height: 844}]) {
      const mobile = viewport.width < 500;
      const page = await browser.newPage({viewport, reducedMotion: mobile ? "reduce" : "no-preference"});
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      page.on("response", response => { if (response.status() >= 400) errors.push(response.url()); });
      await page.goto(url);
      await page.waitForFunction(() => !!window.mathscenePlayer);
      await page.evaluate(() => document.fonts.ready);
      const info = await page.evaluate(() => window.MATHSCENE_LESSON);
      const steps = page.locator("#steps button");
      for (let i = 0; i < info.scenes.length; i++) {
        const scene = info.scenes[i];
        await steps.nth(i).click();
        if (await steps.nth(i).getAttribute("aria-current") !== "step") throw Error("stage button did not seek");
        const times = [0, ...scene.events.map(e => e.at), Math.max(0, scene.duration - 1 / info.canvas.fps)];
        for (const local of new Set(times)) {
          const measured = await page.evaluate(time => {
            mathscenePlayer.seek(time);
            const stage = document.querySelector("#stage").getBoundingClientRect();
            const header = document.querySelector(".stage-header").getBoundingClientRect();
            const labels = Array.from(document.querySelectorAll("#math > [data-layer]")).map(el => {
              const rect = (el.querySelector(".formula-box > span") ?? el).getBoundingClientRect();
              return {id: el.dataset.layer, type: el.dataset.type, left: rect.left, right: rect.right,
                top: rect.top, bottom: rect.bottom};
            });
            const outside = labels.filter(r => r.left < stage.left - 1 || r.right > stage.right + 1 ||
              r.top < stage.top - 1 || r.bottom > stage.bottom + 1).map(r => r.id);
            if (header.bottom > stage.top + stage.height * .1565) outside.push("stage title");
            const text = labels.filter(r => ["formula", "text"].includes(r.type));
            const overlaps = [];
            for (let a = 0; a < text.length; a++) for (let b = a + 1; b < text.length; b++) {
              const p = text[a], q = text[b];
              if (Math.min(p.right, q.right) - Math.max(p.left, q.left) > 3 &&
                  Math.min(p.bottom, q.bottom) - Math.max(p.top, q.top) > 3) overlaps.push(p.id + "/" + q.id);
            }
            const overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
            return {outside, overlaps, overflow, overlay: mathscenePlayer.overlay, index: mathscenePlayer.state.index};
          }, scene.start + local);
          report.samples++;
          if (measured.index !== i) throw Error("scene time mapping failed for " + scene.id);
          if (measured.outside.length || measured.overflow) throw Error("clipped content in " + scene.id + ": " + measured.outside.join(", "));
          checkMotion({maxJointPixelsPerFrame: 0, maxFootPixelsPerFrame: 0}, info, i, measured.overlay, null, info.canvas.fps);
          report.overlapWarnings.push(...measured.overlaps.map(pair => scene.id + "/" + pair));
        }
        const sliders = page.locator("#sliders input");
        for (let k = 0; k < await sliders.count(); k++) {
          const slider = sliders.nth(k);
          const before = await page.locator("#math").innerHTML();
          const bound = scene.interactions[k];
          const values = [bound.min, bound.max, bound.min + bound.step, bound.max - bound.step];
          let changed = false;
          for (const value of new Set(values)) {
            await slider.evaluate((input, value) => {
              input.value = value;
              input.dispatchEvent(new Event("input", {bubbles: true}));
            }, value);
            if (await page.locator("#math").innerHTML() !== before) changed = true;
          }
          if (!changed) {
            const boundLayer = scene.layers.some(layer => layer.type === "stick" && Object.keys(layer.bind ?? {}).length);
            if (!boundLayer) throw Error("slider did not change the visual output: " + bound.id);
          }
          await slider.evaluate((input, value) => {
            input.value = value;
            input.dispatchEvent(new Event("input", {bubbles: true}));
          }, bound.default);
          report.controls++;
        }
        const mode = mobile ? "mobile" : "desktop";
        await page.locator("#stage").screenshot({path: join(work, mode + "-" + scene.id + ".png")});
        if (!mobile && i === Math.min(2, info.scenes.length - 1)) await page.screenshot({path: preview});
      }
      await steps.first().click();
      await page.locator("h1").click();
      if (info.scenes.length > 1) {
        await page.keyboard.press("ArrowRight");
        if (await steps.nth(1).getAttribute("aria-current") !== "step") throw Error("keyboard navigation failed");
      }
      await steps.first().click();
      await page.locator("#play").click();
      await page.waitForFunction(() => Number(document.querySelector("#seek").value) > 0);
      await page.locator("#play").click();
      if (await page.locator("#play").textContent() !== "재생") throw Error("pause control failed");
      if (errors.length) throw Error(errors.join("\n"));
      report.viewports.push(viewport.width);
      await page.close();
    }
    const offline = await browser.newPage({offline: true});
    await offline.goto(pathToFileURL(join(web, "index.html")).href);
    await offline.waitForFunction(() => !!window.mathscenePlayer);
    report.offlineFile = true;
    report.overlapWarnings = [...new Set(report.overlapWarnings)];
    await writeFile(join(work, "browser.json"), JSON.stringify(report, null, 2));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}

try {
  if (command === "prepare") await prepare(...args);
  else if (command === "capture") await capture(...args);
  else if (command === "verify") await verify(...args);
  else if (command === "doctor") {
    const browser = await launch();
    console.log("Chromium " + browser.version());
    await browser.close();
  } else throw Error("unknown bridge command");
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
