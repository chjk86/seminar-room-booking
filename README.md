# 대학원 세미나실 예약 시스템

세미나실 1개를 대상으로, 로그인 없이 이름만 입력해 실시간으로 예약/취소할 수 있는
모바일 친화적 웹 앱입니다. 스마트폰 브라우저에서 접속해 "홈 화면에 추가"하면
아이콘을 눌러 앱처럼 바로 실행할 수 있습니다 (PWA).

## 구성
- `app/main.py` : FastAPI 백엔드 (예약 생성/조회/취소 API, SQLite 저장)
- `app/static/index.html` : 모바일 웹 화면 (날짜 선택, 예약 현황, 예약/취소 폼)
- `app/static/manifest.json`, `sw.js`, `icon.png` : 홈 화면 추가(PWA) 지원
- `requirements.txt` : 필요한 파이썬 패키지

## 1. 로컬에서 실행하기

```bash
cd seminar-room-booking
python3 -m venv venv
source venv/bin/activate      # Windows는 venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

실행 후 컴퓨터 브라우저에서 http://localhost:8000 접속하면 화면이 보입니다.

## 2. 휴대폰(같은 와이파이)에서 접속하기

1. 서버를 실행 중인 컴퓨터의 IP 주소를 확인합니다.
   - macOS/Linux: `ifconfig` 또는 `ip addr` (예: 192.168.0.12)
   - Windows: `ipconfig` (IPv4 주소)
2. 휴대폰이 **같은 와이파이**에 연결되어 있는지 확인합니다.
3. 휴대폰 브라우저에서 `http://192.168.0.12:8000` 처럼 접속합니다.
4. 크롬/사파리 메뉴에서 "홈 화면에 추가"를 하면 앱 아이콘처럼 사용할 수 있습니다.

이 방식은 컴퓨터가 켜져 있고 같은 네트워크에 있을 때만 동작합니다.
학과 교수님/학생 100여 명이 언제든 외부에서도 접속하려면 아래 3번처럼
클라우드에 올리는 것을 권장합니다.

## 3. 인터넷 어디서나 접속 가능하게 배포하기 (무료 티어 예시: Render)

1. 이 폴더를 GitHub 저장소에 올립니다.
2. https://render.com 가입 후 "New Web Service" 생성, 방금 만든 저장소 연결.
3. 설정값:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 배포가 끝나면 `https://프로젝트이름.onrender.com` 같은 고정 주소가 생기고,
   이 주소를 교수님/학생들에게 공유하면 각자 휴대폰에서 접속할 수 있습니다.
5. (Railway, Fly.io 등 다른 클라우드도 동일한 방식으로 배포 가능합니다.)

무료 플랜은 트래픽이 없으면 서버가 잠들었다가 첫 접속 시 몇 초 느릴 수 있습니다.
100명 규모, 세미나실 1개 스케줄이라면 무료 플랜으로 충분합니다.

## 4. 설정 값 바꾸기

`app/main.py` 상단의 다음 값들을 수정하면 됩니다.

```python
ROOM_NAME = "대학원 세미나실"   # 화면에 표시될 방 이름
OPEN_TIME = "09:00"            # 예약 가능 시작 시각
CLOSE_TIME = "22:00"           # 예약 가능 종료 시각
SLOT_MINUTES = 30              # 시간 입력 단위(분)
```

## 5. 동작 방식 요약
- 예약 시 이름, 날짜, 시작/종료 시간, 용도(선택)를 입력합니다.
- 같은 시간대에 이미 예약이 있으면 서버가 거부합니다 (중복 예약 방지).
- 취소 시 예약자 이름을 다시 입력해야 하며, 예약 시 이름과 일치해야 취소됩니다.
  (로그인이 없으므로 완벽한 보안은 아니며, 최소한의 오남용 방지 장치입니다.)
- 화면은 3초마다 자동으로 새로고침되어, 다른 사람이 예약/취소하면
  거의 실시간으로 반영됩니다.

## 데이터 백업
예약 데이터는 `app/reservations.db` (SQLite 파일)에 저장됩니다.
이 파일만 복사해두면 예약 내역을 백업/복원할 수 있습니다.
