# 문제 해결

- `stickman-lecture doctor`에서 브라우저가 누락되면 `npm run browser:install`을 실행한다. 이미 설치된 Chromium을 쓰려면 `MATHSCENE_CHROMIUM`에 실행 파일의 절대 경로를 넣는다.
- npm 캐시 권한 오류가 나면 `npm ci --cache .venv/npm-cache`처럼 쓰기 가능한 별도 캐시를 쓴다.
- ManimCE 설치 중 Cairo나 Pango 헤더가 누락되면 README의 시스템 패키지를 설치하고 다시 시도한다.
- 한국어가 깨지면 브라우저 캡처 호스트와 영상 호스트에 Noto Sans CJK KR 등의 글꼴을 설치한다. Pango 영상 글꼴은 `MATHSCENE_KOREAN_FONT`로 선택할 수 있다. 웹 및 캡처의 글꼴은 시스템 폴백을 사용한다.
- 수식 오류는 `prepare.log` 또는 `verify.log`에서 확인한다. 기본 및 AMS TeX 표현을 사용하고 장면의 `symbols`를 확인한다.
- 일시적으로 프레임 해상도를 낮추려면 `--preview`로 렌더한다. 영상 단계가 실패한 경우 `--mode web`으로 독립 결과를 만들 수 있다.
- 파일을 직접 열었을 때 자산이 보이지 않으면 `python -m http.server 8000 --directory output/mlp/web`을 프로젝트 루트에서 실행해 확인한다.
- 다른 작업 디렉터리에서 Node 모듈을 찾지 못하면 npm을 설치한 프로젝트의 절대 경로를 `MATHSCENE_NODE_HOME`에 지정한다.
