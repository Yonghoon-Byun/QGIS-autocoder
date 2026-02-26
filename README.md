# QGIS AI Auto-Coder

자연어로 PyQGIS 코드를 생성하고 즉시 실행하는 QGIS 플러그인.

> "레이어 이름을 모두 출력해줘" → AI가 PyQGIS 코드 생성 → QGIS에서 바로 실행

---

## 주요 기능

- **자연어 → 코드**: 한국어/영어 자연어 요청을 PyQGIS 실행 코드로 변환
- **다중 LLM 지원**: OpenAI, Claude(Anthropic), Ollama(로컬), OpenAI 호환 API
- **자동 실행**: 생성된 코드를 즉시 실행하거나 검토 후 수동 실행
- **자동 재시도**: 실행 오류 발생 시 에러를 LLM에 피드백하여 자동 수정
- **컨텍스트 인식**: 현재 QGIS 프로젝트의 레이어, CRS, 맵 범위 등을 자동으로 LLM에 제공
- **대화 히스토리**: 연속 대화를 통한 반복적 코드 개선 지원

---

## 지원 LLM 제공자

| 제공자 | 모델 예시 | API 키 |
|--------|----------|--------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo | 필요 (`sk-...`) |
| Claude | claude-sonnet-4, claude-3-5-sonnet | 필요 (`sk-ant-...`) |
| Ollama | llama3.1, codellama, deepseek-coder | 불필요 (로컬) |
| OpenAI 호환 | LM Studio, LocalAI 등 | 선택사항 |

---

## 요구사항

- **QGIS**: 3.16 이상
- **Python**: 3.x (QGIS 번들)
- **PyQt5**: QGIS 번들 포함
- **requests** (선택): `pip install requests` — 없으면 `urllib` 자동 사용

---

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/Yonghoon-Byun/QGIS-autocoder.git
```

### 2. QGIS 플러그인 폴더에 복사

플러그인 폴더 위치:
- **Windows**: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

```bash
# 예시 (Windows)
xcopy /E /I QGIS-autocoder "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\QGIS-autocoder"
```

### 3. QGIS에서 플러그인 활성화

`플러그인` → `플러그인 관리 및 설치` → `설치된 플러그인` → **QGIS AI Auto-Coder** 체크

---

## 사용법

### 1. 플러그인 실행

툴바의 **AI Auto-Coder** 버튼 클릭 또는 메뉴 `플러그인` → `AI Auto-Coder` → `AI Auto-Coder`

### 2. LLM 설정 (우측 패널)

1. **제공자** 선택 (OpenAI / Claude / Ollama / OpenAI 호환)
2. **API 키** 입력 (Ollama는 불필요)
3. **모델** 선택
4. **설정 저장** 클릭

### 3. 코드 생성 및 실행

입력창에 자연어로 요청 후 **전송** (또는 `Enter`):

```
예시 요청:
- "현재 프로젝트의 모든 레이어 이름을 출력해줘"
- "선택된 피처의 면적을 제곱미터로 계산해줘"
- "road 레이어를 빨간색으로 스타일 변경해줘"
- "현재 레이어에서 인구 > 10000인 피처만 선택해줘"
```

생성된 코드는 코드 에디터에서 확인 후 **실행** 버튼으로 실행.

### 4. 실행 옵션

| 옵션 | 설명 |
|------|------|
| 코드 생성 후 자동 실행 | 코드 확인 없이 즉시 실행 |
| 생성된 코드 표시 | 코드 에디터 영역 표시/숨김 |
| 에러 시 자동 재시도 | 실행 오류를 LLM에 전달하여 자동 수정 시도 |

---

## 프로젝트 구조

```
QGIS-autocoder/
├── __init__.py              # QGIS 플러그인 진입점
├── plugin_main.py           # 메인 플러그인 클래스 (오케스트레이터)
├── ui_dialog.py             # PyQt5 UI 컴포넌트 전체
├── metadata.txt             # QGIS 플러그인 메타데이터
├── core/
│   ├── context_builder.py   # QGIS 프로젝트 컨텍스트 수집
│   ├── prompt_manager.py    # 시스템 프롬프트 및 대화 히스토리 관리
│   └── code_executor.py     # 코드 추출, 검증, exec() 실행
├── llm_providers/
│   ├── base_provider.py     # LLM 제공자 추상 베이스 클래스
│   ├── openai_provider.py   # OpenAI API
│   ├── claude_provider.py   # Anthropic Claude API
│   ├── ollama_provider.py   # Ollama 로컬 API
│   └── openai_compat_provider.py  # OpenAI 호환 API
├── workers/
│   └── api_worker.py        # QThread 기반 비동기 API 호출
└── resources/
    └── icon.svg             # 플러그인 아이콘
```

---

## 실행 환경 (코드 내 기본 제공)

생성된 코드 실행 시 다음 변수/모듈이 자동으로 주입됩니다:

```python
iface          # QgisInterface
QgsProject     # 프로젝트 관리
QgsVectorLayer, QgsRasterLayer
QgsFeature, QgsGeometry, QgsField
QgsCoordinateReferenceSystem
processing     # Processing Toolbox
QColor, QFont, QMessageBox  # PyQt5
# ... 그 외 30개 이상의 QGIS 클래스
```

---

## Ollama 로컬 모델 사용

인터넷 연결 없이 로컬에서 실행하려면 [Ollama](https://ollama.ai)를 설치하세요:

```bash
# Ollama 설치 후 모델 다운로드
ollama pull codellama
ollama pull deepseek-coder
ollama pull qwen2.5-coder
```

플러그인에서 제공자를 **Ollama**, Base URL을 `http://localhost:11434`으로 설정.

---

## 라이선스

MIT License

---

## 기여

버그 리포트 및 기능 제안은 [Issues](https://github.com/Yonghoon-Byun/QGIS-autocoder/issues)에 등록해주세요.
