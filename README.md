# StickMan Lecture · 졸라맨 강의

졸라맨 강의는 원본 Stick Scene 캐릭터가 소품을 움직이며 개념을 설명하는 Codex 스킬이다. 캐릭터가 수레를 밀면 관측점과 추정점이 함께 움직인다. 같은 장면 파일에서 MP4 영상과 직접 조작할 수 있는 HTML 강의를 만들 수 있다.

| 그래프 그리기 · 칼만 필터의 분포 갱신 | 물체 조작 · 수레와 함께 움직이는 그래프 |
| --- | --- |
| ![예측, 관측 우도와 사후 분포의 곡선을 차례로 그린다](media/kalman-update.gif) | ![캐릭터가 수레를 밀며 관측점과 추정점의 움직임을 보여 준다](media/stick-interaction.gif) |
| [22초 MP4](media/kalman-update.mp4) | [30.6초 MP4](media/stick-interaction.mp4) |

## 설치

macOS에서 Python 3.11 이상과 Node.js 22.12 이상을 사용한다. 프로젝트의 가상 환경을 활성화한 상태에서 Codex를 시작하면 `$stickman-lecture`를 호출할 수 있다.

```bash
git clone https://github.com/choimagon/stickman_lecture.git
cd stickman_lecture
brew install python node ffmpeg cairo pango pkg-config
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[video,test]'
npm ci
npm run browser:install
stickman-lecture doctor --video
./scripts/install-skill.sh
```

Ubuntu 계열 Linux에서는 Python 3.11 이상과 Node.js 22.12 이상을 준비하고 다음 패키지를 설치한 뒤 위의 가상 환경 및 npm 명령을 사용한다. Chromium 시스템 라이브러리가 추가로 필요하면 `npx playwright install --with-deps chromium`을 실행한다.

```bash
sudo apt install python3-venv python3-dev build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg fonts-noto-cjk
```

웹 전용 설치는 `python -m pip install -e '.[test]'`과 `stickman-lecture doctor`를 사용한다. 두 모드의 검증에 Chromium이 필요하다. LaTeX 배포판은 필요 없다.

## 사용하기

Codex에서 다음처럼 요청한다.

```text
$stickman-lecture 졸라맨이 수레를 밀면 칼만 추정점이 움직이는 모습을 MP4와 조작 가능한 HTML 둘 다로 만들어줘
```

MP4, 조작 가능한 HTML, 둘 다 중 원하는 형식을 적는다. 형식을 지정하지 않으면 스킬이 제작 전에 먼저 묻고 답을 기다린다.

포함된 장면을 직접 검증하고 영상과 웹으로 렌더링할 수도 있다.

```bash
stickman-lecture validate examples/stick-interaction/scene.json
stickman-lecture render examples/stick-interaction/scene.json --mode both
```

영상 출력의 `player.html`은 함께 저장된 `lesson.mp4`를 재생한다. 장면 목록에서 원하는 장면으로 이동할 수 있고 재생 위치에 따라 현재 장면이 표시된다. 두 파일을 함께 보관하면 오프라인으로 열 수 있다.

웹 출력의 `web/index.html`은 슬라이더 같은 요소를 직접 조작하는 별도의 결과물이다. 웹 폴더를 함께 보관하면 오프라인으로 열 수 있다. 영상은 슬라이더의 기본값으로 렌더링된다. `--mode video` 또는 `--mode web`으로 필요한 결과만 선택할 수도 있다.

영상은 말풍선 글자 수에 맞춰 읽는 시간을 자동으로 조정하고 효과음을 추가한다. 원래 장면 시간을 사용하려면 `--fixed-timing`, 모든 효과음을 끄려면 `--no-effects`를 지정한다. 말풍선 효과음만 끄는 `--no-bubble-sound`와 음원을 추가하는 `--audio`도 사용할 수 있다. `captions.srt`에는 영상 대사가 들어 있다.

## 예제

| 데모 | 모드 | 내용 |
| --- | --- | --- |
| [수레를 밀어 보는 칼만 갱신](examples/stick-interaction/storyboard.md) | `both` | 수레, 관측점, 추정점과 갱신식 |
| [칼만 필터](examples/kalman-filter/storyboard.md) | `video` | 예측 분포, 관측 우도와 사후 분포 |

[전체 예제](examples/)는 `./scripts/render-demos.sh`로 재현할 수 있다. 출력 경로는 `--out`으로 변경할 수 있다.

## 개발과 문서

```bash
python -m pytest -q
stickman-lecture doctor --video
```

[스킬과 저작 템플릿](skills/stickman-lecture/SKILL.md), [장면 계약](skills/stickman-lecture/references/scene-schema.md), [아키텍처](docs/ARCHITECTURE.md), [문제 해결](docs/TROUBLESHOOTING.md), [실행 결과와 제한](docs/IMPLEMENTATION_STATUS.md), [소스 조사](docs/SOURCE_ANALYSIS.md), [라이선스](LICENSES.md)를 참고한다.
