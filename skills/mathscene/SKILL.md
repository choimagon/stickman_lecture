---
name: mathscene
description: Create Korean or multilingual math, AI, robotics, or algorithms lessons with synchronized equations, diagrams, and a stick figure narrator. Use when asked for an educational animation, narrated visual explanation, interactive lesson with sliders, or MP4 and HTML versions from one storyboard.
---

# MathScene

Create a lesson from one validated Scene IR. Use Korean and an undergraduate level unless the user specifies otherwise. Default to MP4, use web for interaction, and use both when both deliverables are requested.

1. Write the storyboard before drafting `scene.json`. Use [pedagogy](references/pedagogy.md) and the [storyboard template](templates/storyboard.md). Define the input, learning goal, and one observable takeaway for each scene.
2. Author `scene.json` with [the Scene IR contract](references/scene-schema.md) and [the JSON template](templates/lesson.json). Put numeric assertions next to important calculations and keep a stable legend across scenes. Consult [visual layout](references/visual-style.md) and [stick timing](references/stick.md). For MP4, also consult [video rendering](references/manim.md).
3. Use the installed `mathscene` CLI. Run `mathscene doctor --video` for video or both, and `mathscene doctor` for web. If the CLI is outside PATH, use the venv or the project installation instructions. Validate with `mathscene validate /absolute/path/scene.json`. Render with `mathscene render /absolute/path/scene.json --mode video|web|both --out /absolute/path/output`.
4. Open the selected outputs. Follow [validation](references/validation.md) for numerical checks, frame inspection, and web controls. Fix only observed problems and retry up to two times, preserving the logs and any usable alternative output.
5. Deliver the lesson, storyboard, Scene IR, preview, and validation report. For video, also link the SRT if produced. Report concrete failures and the scope of verification.

Author data and use the supplied runtime. For expressions, use the declarative operators in the contract. Web calculates slider changes in the browser. Video uses default slider values and optional local audio.
