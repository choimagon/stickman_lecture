# Scene IR 0.1

`scene.json`은 수식, 도형, 캐릭터, 자막과 시간을 함께 저장한다. 설치한 프로젝트의 `src/mathscene/resources/schema.json`이 구조를 정의한다. 기본 좌표는 1280×720 논리 픽셀이다. 원점은 좌상단이다. 시간 단위는 초이며 프레임 경계에 맞춘다.

- 루트에 `version: "0.1"`, `title`, `locale`, `audience`, `duration`, `canvas`, `theme: "dark-academic"`, `definitions`, `scenes`, `exports`를 둔다. `exports`는 저자의 권장 모드이며 실제 내보내기는 CLI에서 선택한다.
- 장면에 `id`, `stage`, `title`, `start`, `duration`, `learning_goal`, `narration`, `layers`, `events`를 둔다. 구간은 0초부터 연속이다.
- `definitions`는 `{symbol, meaning}` 배열이다. 각 수식의 `symbols`에 정의 이름을 적는다. 수식 문자열의 기호 일치는 사람이 확인한다.
- `text`는 `x,y,text`, `formula`는 `x,y,tex,symbols`가 필요하다. `size`의 기본값은 32다. `align`은 `left`, `center`, `right`다. y 좌표는 세로 가운데다.
- `line`, `vector`는 `x1,y1,x2,y2`가 필요하다. `circle`은 중심 `x,y`와 `r`을 사용한다. `rect`는 좌상단 `x,y`와 `w,h`를 사용한다. `width`는 선 두께, `fill`은 채우기 색이다.
- `gaussian`은 `x,y,w,h,min,max,mean,sigma`가 필요하다. `x,y`는 그래프 상자의 좌상단이다. 바닥선은 `y+h`이고 봉우리 높이는 `h/sigma`다. 같은 축에서 비교할 때 동일한 상자를 쓴다. 축과 눈금은 `line` 및 `text`로 추가한다.
- `stick`은 발 기준 `x,y`, `pose`, 선택 `bubble`, `scale`을 사용한다.
- 이벤트는 `{at,action,target}` 형태다. `at`는 장면 시작 기준 상대 초다. `show` 대상은 첫 표시 전 숨는다. `hide`는 숨긴다. `gesture`에는 `value`로 자세를 지정한다. 수식 교체는 같은 시점의 `hide`와 `show`로 표현한다.
- 슬라이더는 장면의 `interactions`에 `{id,label,min,max,step,default}`를 둔다. 레이어의 `bind`는 기존 필드를 덮어쓴다. 숫자는 그대로 사용하고, 문자열이 슬라이더 ID와 일치하면 해당 값을 사용한다. 나머지 문자열은 리터럴이다.

```json
{"text": ["concat", "출력 = ", ["round", ["mul", 2, "x1"], 2]]}
```

연산은 `add`, `sub`, `mul`, `div`, `max`, `pow`, `sqrt`, `exp`, `lt`, `select`, `round`, `concat`이다. `lt`는 작음 비교이며 `select`는 조건, 참일 때 값, 거짓일 때 값을 받는다. `round`의 두 번째 인자는 생략할 수도 있다. 슬라이더 경계값과 중간값에서 0으로 나누거나 도형이 화면 밖으로 나가지 않게 한다.

`checks`는 선택이다. 각 검사에 `kind`가 필요하다. `kind: "sample"`은 `scene,inputs,actual,expected`로 수치 대입을 검사한다. `kind: "equivalent"`는 `left,right,symbols`로 지원 연산의 실수 기호식을 비교한다. `kind: "shape"`는 `left,right,expected`에 행과 열 크기를 주어 행렬 곱의 차원을 검사한다.

```json
{"kind":"sample","scene":"insight","inputs":{"x1":4},"actual":["mul",2,"x1"],"expected":8}
```
