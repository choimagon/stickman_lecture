---
name: stickman-lecture
description: Create sketch-style videos and interactive HTML using the original Stick Scene actor. Animate the character moving props and show the result in diagrams, graphs, and equations. Use for visual explanations, process walkthroughs, math, and AI lessons.
---

# 졸라맨 강의

영문 표기는 **StickMan Lecture**다.

원본 Stick Scene 리그로 인물이 직접 행동하는 설명을 만든다. 예시가 필요한 개념에서는 인물이 수레를 밀거나, 블록을 옮기거나, 레버를 당기는 장면으로 관계를 먼저 보여 준다. 바뀌는 양을 그래프와 숫자에 연결하고 관찰한 관계를 수식으로 정리한다. 기본 테마는 `stick-studio`다. 언어 요청이 없으면 한국어로 설명한다.

**출력 형식은 제작 전에 확정한다.** 사용자의 요청이나 앞선 대화에 MP4, 조작 가능한 HTML, 둘 다 중 하나가 명시되어 있지 않으면 “MP4, 조작 가능한 HTML, 둘 다 중 어떤 형식으로 만들까요?”라고 먼저 묻고 답을 받을 때까지 제작하지 않는다. 형식이 명시되어 있으면 다시 묻지 않는다. 각각 `--mode video`, `--mode web`, `--mode both`를 사용한다. MP4에 함께 제공되는 장면 탐색용 `player.html`은 별도의 조작 가능한 HTML 출력과 구분한다.

1. [스토리보드 템플릿](templates/storyboard.md)에 초기 상태, 인물의 행동, 반응, 관찰할 양, 결과를 기획한다. [행동으로 설명하기](references/interaction.md)와 [설명 설계](references/pedagogy.md)를 따라 장면을 만든다. 조작하는 동안은 행동이 잘 보이도록 말풍선을 쉬게 할 수 있다. 사용자가 짧게 요청하면 장면을 압축한다.
2. [공통 장면 계약](references/scene-schema.md)과 [JSON 템플릿](templates/lesson.json)을 사용한다. `tracks`와 `bind`로 물체 좌표와 그래프, 수치를 같은 입력에 연결한다. `touch`와 `grip`으로 손이 맞닿는 지점과 시각을 지정한다. 화살표와 그래프를 새로 그릴 때는 `draw`를 쓰고 짚을 점은 `speak`로 설명한다. [배치](references/visual-style.md), [자세와 말풍선](references/stick.md), [영상 렌더링](references/manim.md)을 참고한다.
3. `stickman-lecture doctor --video`로 환경을 검사한다. 웹 전용이면 `--video`를 생략한다. 명령이 PATH에 없으면 이 스킬의 실제 경로가 속한 프로젝트에서 `.venv/bin/stickman-lecture`를 찾는다. `stickman-lecture validate /절대/경로/scene.json`으로 장면을 검사한 뒤 `stickman-lecture render /절대/경로/scene.json --mode video|web|both --out /절대/경로/output`을 실행한다. 영상은 말풍선 글자 수에 맞춰 읽는 시간을 자동으로 조정하고 그리는 속도는 유지한다. 원래 시간을 사용하려면 `--fixed-timing`을 지정한다. `both` 모드의 웹은 영상과 같은 시간표를 사용한다. MP4에는 말풍선과 그래프, 선, 화살표, 도형, 점, 수식의 등장에 맞는 효과음이 기본으로 들어간다. `--no-bubble-sound`는 말풍선 효과음만 끄고 `--no-effects`는 모든 효과음을 끈다. 준비한 음원은 `--audio /경로/파일`로 함께 추가한다.
4. 접근, 손이 닿는 순간, 조작 중간, 결과 유지 프레임을 확인한다. 물체와 손, 그래프 점과 수치의 대응을 검증한다. 화면 요소가 서로 가리지 않는지 살피고 입력 제어가 있다면 최솟값·기본값·최댓값에서 조작한다. [검증 지침](references/validation.md)을 참고한다. 관찰한 오류를 고쳐 최대 두 번 다시 렌더한다.
5. 결과물, 스토리보드, 장면 파일, 미리보기, 검증 결과를 전달한다. 영상과 함께 장면 선택이 가능한 `player.html`도 전달한다. SRT는 접근용 별도 대사 파일이다. 화면에서 보이는 설명은 캐릭터 말풍선으로 배치한다.
