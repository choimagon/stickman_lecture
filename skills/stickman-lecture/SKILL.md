---
name: stickman-lecture
description: Draw and animate diagrams, shapes, graphs, networks, and step-by-step visual explanations with a stick-figure teacher and speech bubbles. Use for sketch-style lessons, process walkthroughs, explainer videos, and interactive HTML, including math and AI when relevant.
---

# 스틱맨렉처

도형과 연결을 그리면서 개념이나 과정을 설명한다. 기본은 원본 Stick의 종이와 손그림 지면선을 참고한 `stick-studio` 테마, 한국어, 충분한 설명을 가진 MP4다. 조작이 필요하면 HTML, 두 형식을 요청하면 `both`를 사용한다. 대상 수준을 지정하지 않으면 처음 접하는 성인도 따라올 수 있게 설명한다. 수식은 이해에 도움이 될 때 넣는다.

1. [스토리보드 템플릿](templates/storyboard.md)에 문제, 구성 요소, 관계나 방향, 중간 변화, 결과를 기획한다. 각 요소마다 무엇인지, 왜 필요한지, 앞뒤 요소와 어떻게 이어지는지 설명한다. 요청에 간단히 또는 짧게가 명시된 경우 장면을 압축한다. 기본은 읽을 시간이 충분한 상세 설명이다. [설명 설계 지침](references/pedagogy.md)을 참고한다.
2. 스토리보드를 [공통 장면 계약](references/scene-schema.md)과 [JSON 템플릿](templates/lesson.json)에 옮긴다. 바탕 도형을 먼저 놓고, 이동 방향에 맞춰 화살표와 그래프를 `draw`로 차례대로 긋는다. 요소를 설명할 때 `speak`로 스틱 설명자의 말풍선을 바꾸고 레이블이나 색을 해당 요소에 맞춘다. [배치](references/visual-style.md)와 [말풍선 및 자세](references/stick.md)를 확인한다. 영상이면 [영상 렌더링](references/manim.md)도 참고한다.
3. 설치된 `stickman-lecture doctor --video`로 환경을 검사한다. 웹 전용이면 `--video`를 생략한다. `stickman-lecture validate /절대/경로/scene.json`으로 장면을 검사한 뒤 `stickman-lecture render /절대/경로/scene.json --mode video|web|both --out /절대/경로/output`을 실행한다.
4. 두 형식에서 시작, 그리는 중간, 그린 직후의 프레임을 확인한다. 말풍선과 화살촉, 수식이나 레이블이 서로 가리지 않는지 보고, 입력 제어가 있다면 최솟값·기본값·최댓값에서 실제 화면을 조작한다. [검증 지침](references/validation.md)을 참고한다. 관찰한 오류를 고쳐 최대 두 번 다시 렌더한다.
5. 결과물, 스토리보드, 장면 파일, 미리보기, 검증 결과를 전달한다. 영상의 SRT는 접근용 별도 대사 파일이다. 화면에서 보이는 설명은 캐릭터 말풍선으로 배치한다.
