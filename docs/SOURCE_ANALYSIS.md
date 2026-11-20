# 상류 소스 분석

조사일 2026-11-20. 세 저장소를 임시 디렉터리에 실제 복제하고 해당 HEAD의 파일을 확인했다. 다음 SHA는 조사 시점의 스냅샷이며 이후 상류 변경을 포함하지 않는다.

| 저장소 | 조사한 커밋 | 라이선스와 결정 |
| --- | --- | --- |
| [nilbuild/stick-scene](https://github.com/nilbuild/stick-scene) | `ca84311177a020c2dff7dfd9cb2e7b786288c1ab` | MIT. 런타임과 검사 방식을 분석하고 별도의 결정적 Canvas 캐릭터를 작성한다. |
| [adithya-s-k/manim_skill](https://github.com/adithya-s-k/manim_skill) | `cef045011722d285692e3381d12d4d637da56e18` | 저장소 및 CE 자료는 MIT. ManimGL 하위 자료는 별도 CC BY-NC-SA 4.0. CE만 사용하며 GL 코드는 가져오지 않는다. |
| [subinium/3b1b-style-animation-skill](https://github.com/subinium/3b1b-style-animation-skill) | `a47d18084300b3605512aa956236444f7e52bcba` | MIT. 교육 원칙을 참고하고 로고와 고유 에셋은 사용하지 않는다. |

## Stick 런타임

`runtime/stick.js`는 Canvas 리깅과 `window.RIG` 유틸리티, `window.SCENES` 장면 등록, `window.STICK` 뷰 관리 객체를 제공한다. `templates/scene.js`는 `SCENES[id]`에 `dur`, `width`, `label`, `draw(g, S)`를 등록한다. 기본 좌표는 바닥이 y=0이고 위쪽이 음수다. 포즈와 이동은 `P`, `mix`, `legs`, `walkSeg`, `fig` 등의 도구로 구성한다. CSS 크기와 장면 너비에 맞춰 축척하며 기기 픽셀 비율은 최대 2다.

`<stick-scene>`은 click, hover, view, loop, idle 모드를 지원한다. Canvas는 스크린 리더에서 숨기고 요소에 이미지 역할과 레이블을 부여한다. 작동 가능한 요소에는 Enter 및 스페이스 키 입력이 제공되며 시스템의 reduced-motion 설정을 고려한다. 기본 글꼴은 외부 Google Fonts를 요청할 수 있고 `no-font` 속성으로 끌 수 있다.

외부 시간 지정이 전혀 없는 것은 아니다. `STICK.at(el, {idle: seconds})` 또는 `STICK.at(el, {u: fraction, t: seconds})`는 뷰를 일시 정지하고 즉시 그리는 정지 프레임용 API다. action의 초는 `u = seconds / dur`로 변환할 수 있다. 재생 및 일시정지와 연동한 범용 미디어 타임라인 API라는 의미는 아니다. 기본 바닥과 지면은 각각 `no-floor`, `no-ground`로 끌 수 있고 캔버스를 먼저 지우므로 투명 배경 레이어 구성에 활용 가능하다. 원본 브라우저 실험에서 바닥과 지면을 끈 PNG에 투명 픽셀이 존재함을 확인했다. FFmpeg 합성 성공을 뜻하지는 않는다.

`scripts/frames.mjs`는 `--scene`, 반복 가능한 `--src`, `--frames`의 `idle:초`, `s:초`, `u:비율`, 출력 크기와 파일 옵션을 받는 Playwright 접촉 시트 도구다. `scripts/motion.mjs`는 60fps 샘플에서 관절 점프, 팔과 얼굴 교차, 머리 가림, 팔꿈치 방향, 발 미끄러짐, 손 닿기와 시작 및 종료 불연속 등을 검사한다. 원본 런타임의 특정 문자열을 계측 삽입 지점으로 찾으므로 런타임 변경에 취약하고 자체 캐릭터에 그대로 적용할 수 없다.

채택 결정은 시간에 따라 동일한 프레임을 그리는 독립 Canvas 구현이다. 이는 원본의 전역 DOM 뷰와 자체 씬의 시간 제어를 결합할 필요를 줄인다. 원본 검사기의 판정을 구현하지 않았다면 동등한 검사로 주장하지 않는다.

화면 스타일은 원본 기본 장면을 일반 바닥과 지면으로 다시 렌더링해 비교했다. 원본이 사용하는 흰 배경, 화면 하단의 매우 옅은 회색 바닥, 가늘고 미세하게 흔들리는 검은 경계를 `stick-studio` 테마로 구현했다.

## ManimCE 자료

`skills/manimce-best-practices/SKILL.md`와 `rules/latex.md`, `axes.md`, `graphing.md`, `lines.md`, `transform-animations.md`, `updaters.md`, `cli.md`는 각각 `MathTex`와 `Tex`, `Axes`와 `NumberPlane`, 그래프, `Vector`, `Transform`과 `ReplacementTransform`, `ValueTracker`와 updater, CLI를 설명한다. `Scene.construct()`에서 객체를 만들고 `self.play()`와 `self.wait()`로 시간을 구성한다. `Transform`은 원본 객체 참조에 결과가 남으며 `ReplacementTransform`은 대상을 교체한다. LaTeX와 시스템 렌더링 의존성이 필요하다.

CLI 자료의 `-ql`은 저품질 미리보기, `-qm`은 1280×720과 30fps 설정이다. 개별 해상도, fps, 출력 경로와 투명 형식은 설치된 CE 버전의 CLI 도움말 및 실제 결과를 기준으로 검증한다. 오류 코드를 확인하고 실패 로그와 중간 파일을 남긴다. 고정 시간 재생은 프레임 수와 fps를 실제 출력에서 확인해야 한다.

`skills/manimgl-best-practices/`는 `manimlib` 및 `manimgl`을 쓰는 다른 엔진이다. 동일 API로 취급하거나 예제를 CE에 붙이지 않는다. 영상은 CE의 수학 레이어와 자체 Canvas 캐릭터를 FFmpeg로 합성한다. 브라우저는 Python Manim을 실행하지 않고 KaTeX와 브라우저 그래픽을 쓴다. 양쪽의 의미와 시간을 공통 JSON으로 전달하며 화소 단위 동일성을 가정하지 않는다.

## 교육 설계 자료

`skills/3b1b-style-animation/rules/pedagogy.md`는 필요성 제시, 직관 우선, 구체적 사례에서 일반화, 기호 설명, 한 번에 한 개념, 핵심 통찰 뒤 멈춤, 검증 사례를 강조한다. `layout-spacing.md`, `visual-quality.md`, `equations.md`, `strict-sync.md` 등은 가독성과 동기화를 다룬다. 이 원칙을 독자적인 스토리보드로 재표현하고 시각적 장식보다 수학적 정확성을 우선한다. 특정 영상, 로고, 고유 에셋은 복제하지 않는다. MIT 원문을 실질적으로 복사할 때는 저작권 및 허가 고지를 포함한다.

## 검증 범위

원본 `diffity-loop`를 Chrome 157과 Playwright에서 실행하고 0초, 3.35초, 6.70초, 10.05초 PNG를 추출했다. 마지막 세 시점의 연속 캡처는 바이트가 같았지만 최초 0초는 달랐다. 각 프레임에 투명 픽셀이 있었고 브라우저 페이지 오류는 없었다. 자세한 결과는 `output/technical-probes/stick/`에 있다.

통합 렌더러에서는 ManimCE가 그린 칼만 필터 수식과 가우시안 곡선 위에, Chromium이 캡처한 투명 캐릭터와 말풍선을 FFmpeg로 합성했다. FFprobe에서 각 레이어와 최종 영상 길이는 90초, 프레임 수는 2700으로 일치했다. 장면별 PNG에서 가우시안 곡선, 캐릭터, 말풍선, 수식의 가시성을 확인했다. 다른 데모의 실행 결과는 [구현 현황](IMPLEMENTATION_STATUS.md)에 기록했다.
