# 🎫 Discord Ticket Bot (discord.py 2.x)

Slash Command 기반의 디스코드 티켓 관리 봇입니다. Python 3.11+, discord.py 2.x, SQLite(aiosqlite)를 사용하며,
Render / Replit / iSH(iPhone) / Ubuntu / Windows 등 어떤 환경에서도 동일하게 실행할 수 있습니다.

---

## ✨ 주요 기능

- **티켓 생성**: `/티켓패널` 로 Embed + `Create Ticket` 버튼을 전송, 사용자당 티켓 1개 제한
- **티켓 설정**: `/티켓설정` (카테고리 / 로그채널 / 저장채널 / 관리자역할 / 이름형식 / 확인)
- **관리자 관리**: `/관리자추가`, `/관리자제거` — 관리자만 닫기·삭제·재오픈 가능
- **티켓 저장**: TXT / HTML 트랜스크립트 생성 → 저장채널 업로드 + 다운로드 파일 제공
- **로그**: 생성 / 닫힘 / 재오픈 / 삭제 / 저장 / 관리자 추가·제거 로그
- **권한 제어**: `discord.PermissionOverwrite` 로 티켓 채널 접근 권한 분리
- **SQLite 저장**: 설정, 관리자, 티켓, 사용자별 티켓 보유 여부 저장
- **영구 View**: 버튼에 timeout 없음, 봇 재시작 후에도 계속 동작 (Persistent View)

---

## 📁 프로젝트 구조

```
ticket-bot/
├── bot.py            # 메인 실행 파일, 슬래시 명령어 정의
├── config.py         # .env 환경변수 로딩
├── database.py       # SQLite(aiosqlite) 비동기 DB 레이어
├── ticket.py         # 티켓 생성/닫기/재오픈/삭제/저장 핵심 로직
├── views.py          # Discord UI(View/Button) 정의 (Persistent)
├── utils.py          # Embed, 권한체크, 로그, 트랜스크립트 유틸
├── keep_alive.py      # Replit/Render용 Flask keep-alive 웹서버
├── requirements.txt   # 파이썬 의존성
├── Procfile           # Render/Heroku 스타일 실행 명령
├── render.yaml         # Render 배포 설정
├── .env.example        # 환경변수 예시
├── .gitignore
└── README.md
```

---

## ✅ 요구사항

- Python **3.11 이상**
- 디스코드 봇 토큰 (https://discord.com/developers/applications)
- 봇 초대 시 아래 **Intents** 활성화 필요 (Developer Portal → Bot → Privileged Gateway Intents)
  - `SERVER MEMBERS INTENT`
  - `MESSAGE CONTENT INTENT`

### 봇 권한 (초대 링크 생성 시)

**Scopes**: `bot`, `applications.commands`

**Bot Permissions**:
- View Channels
- Manage Channels
- Manage Roles (권한 오버라이드 설정용)
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Manage Messages

---

## 🚀 설치 및 실행

### 1. 저장소 준비

```bash
git clone <your-repo-url> ticket-bot
cd ticket-bot
```

### 2. 가상환경 생성 (권장)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 만들고 값을 채워주세요.

```bash
cp .env.example .env
```

```
DISCORD_TOKEN=your_bot_token_here
DB_PATH=ticket_bot.db
GUILD_ID=
KEEP_ALIVE=false
PORT=8080
```

### 5. 실행

```bash
python bot.py
```

정상적으로 실행되면 콘솔에 `데이터베이스 연결 완료`, `Persistent View 등록 완료`,
`글로벌 N개의 명령어를 동기화했습니다.` 로그가 출력됩니다.

> 💡 개발 중 슬래시 명령어를 즉시(수 초 내) 반영하고 싶다면 `.env` 의 `GUILD_ID` 에
> 테스트 서버 ID를 입력하세요. 글로벌 동기화는 전파까지 최대 1시간이 걸릴 수 있습니다.

---

## 🖥️ 플랫폼별 실행 가이드

### Windows

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# .env 파일을 메모장으로 열어 DISCORD_TOKEN 입력 후 저장
python bot.py
```

### Ubuntu / Linux

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # DISCORD_TOKEN 입력
python3 bot.py
```

백그라운드로 계속 실행하고 싶다면 `tmux`, `screen`, 또는 `systemd` 서비스 등록을 권장합니다.

### iSH (iPhone)

iSH 는 Alpine Linux 기반 x86 에뮬레이터입니다.

```bash
apk update
apk add python3 py3-pip git
git clone <your-repo-url> ticket-bot
cd ticket-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
vi .env   # DISCORD_TOKEN 입력
python3 bot.py
```

> iSH는 ARM 기기에서 에뮬레이션으로 동작하기 때문에 속도가 느릴 수 있습니다.
> 장시간 구동에는 Render 등 서버 호스팅을 권장합니다.

### Replit

1. Replit에서 **Import from GitHub** 로 이 저장소를 불러옵니다.
2. 좌측 자물쇠(Secrets) 탭에서 아래 값을 등록합니다.
   - `DISCORD_TOKEN` = 봇 토큰
   - `KEEP_ALIVE` = `true`
3. `Run` 버튼을 누르면 `keep_alive.py` 가 자동으로 웹서버(포트 8080)를 띄워
   Replit이 프로세스를 계속 살려둘 수 있습니다.
4. (선택) [UptimeRobot](https://uptimerobot.com) 등으로 Replit 웹 URL을 주기적으로 핑하면
   더 안정적으로 상시 구동됩니다.

### Render

1. GitHub 저장소를 Render에 연결합니다. (`render.yaml` 이 자동으로 인식됩니다)
2. **Environment Variables** 에서 `DISCORD_TOKEN` 을 등록합니다. (Secret이므로 대시보드에서 직접 입력)
3. `KEEP_ALIVE=true`, `PORT` 는 Render가 자동으로 주입하므로 그대로 두면 됩니다.
4. 배포가 완료되면 Web Service 로 봇이 계속 실행되며, `/` 헬스체크 엔드포인트가
   `keep_alive.py` 를 통해 응답합니다.

---

## 🕹️ 명령어 목록

| 명령어 | 설명 | 권한 |
| --- | --- | --- |
| `/티켓패널` | 티켓 생성 패널(Embed+버튼) 전송 | 관리자 |
| `/티켓설정 카테고리` | 티켓 생성 카테고리 설정 | 관리자 |
| `/티켓설정 로그채널` | 로그 채널 설정 | 관리자 |
| `/티켓설정 저장채널` | 저장(트랜스크립트) 채널 설정 | 관리자 |
| `/티켓설정 관리자역할` | 티켓 관리 역할 설정 | 관리자 |
| `/티켓설정 이름형식` | 티켓 채널 이름 형식 설정 (`{count}`, `{username}`) | 관리자 |
| `/티켓설정 확인` | 현재 설정 확인 | 관리자 |
| `/관리자추가` | 티켓 관리자 추가 | 관리자 |
| `/관리자제거` | 티켓 관리자 제거 | 관리자 |
| `/티켓닫기` | 현재 티켓 닫기 | 관리자 |
| `/티켓재오픈` | 닫힌 티켓 재오픈 | 관리자 |
| `/티켓삭제` | 티켓 채널 삭제 (5초 대기 후 삭제) | 관리자 |
| `/티켓저장` | TXT/HTML 로 대화 저장 | 관리자 |

버튼으로도 동일한 기능(닫기 / 재오픈 / TXT 저장 / HTML 저장 / 삭제)을 사용할 수 있습니다.

---

## 🗄️ 데이터베이스 스키마

- `guild_settings` : 서버별 카테고리 / 로그채널 / 저장채널 / 관리자역할 / 이름형식
- `admins` : `/관리자추가` 로 등록된 추가 관리자 목록
- `tickets` : 생성된 모든 티켓의 상태(open/closed), 소유자, 채널, 생성/닫힘 시각
- `ticket_counters` : 서버별 티켓 순번(카운터)

`관리자 권한`은 다음 세 가지 중 하나라도 만족하면 인정됩니다.
1. 디스코드 서버 `Administrator` 권한 보유
2. `/티켓설정 관리자역할` 로 지정된 역할 보유
3. `/관리자추가` 로 등록된 사용자

---

## ❓ 문제 해결 (Troubleshooting)

- **명령어가 디스코드에 보이지 않아요**: 글로벌 동기화는 최대 1시간이 걸릴 수 있습니다.
  빠른 테스트를 원하면 `.env` 의 `GUILD_ID` 에 테스트 서버 ID를 입력하세요.
- **`Privileged Intent` 오류가 발생해요**: Discord Developer Portal → Bot 탭에서
  `SERVER MEMBERS INTENT`, `MESSAGE CONTENT INTENT` 를 켜주세요.
- **채널 생성이 안 돼요**: 봇 역할에 `채널 관리(Manage Channels)` 권한이 있는지,
  봇 역할이 티켓 카테고리보다 낮은 위치에 있지 않은지 확인하세요.
- **Render/Replit에서 봇이 계속 꺼져요**: `.env` 의 `KEEP_ALIVE=true` 로 설정했는지 확인하세요.

---

## 📄 라이선스

이 프로젝트는 자유롭게 수정 및 배포하여 사용할 수 있습니다.
