# 비디오 렌더링

Manim Community Edition의 Cairo 렌더러가 수식, 그래프, 벡터, 텍스트를 그린다. LaTeX 문자열은 MathJax로 SVG 경로로 변환한 뒤 Manim `SVGMobject`로 가져온다. 따라서 이 파이프라인은 시스템 LaTeX를 요구하지 않는다. KaTeX와 MathJax가 모두 지원하는 기본 및 AMS 수식 구문을 우선 사용한다.

이벤트가 나뉘는 프레임마다 수학 레이어를 구성한다. 그래프의 좌표와 화살촉은 웹과 같은 함수에서 계산한다. 슬라이더 값은 영상에서 기본값으로 고정된다. 캐릭터와 자막은 같은 프레임 인덱스의 투명 Canvas로 그린 다음 FFmpeg로 합성한다.

`--preview`는 비디오 픽셀 크기만 줄인다. `--audio /path/to/file`은 사용자가 제공한 오디오를 추가한다. 한국어 Pango 글꼴 선택이 필요할 경우 `MATHSCENE_KOREAN_FONT`를 지정한다.
