<!-- Generated: 2026-02-25 | Updated: 2026-02-25 -->

# QGIS-autocoder (루트)

## Purpose
QGIS AI Auto-Coder 플러그인의 루트 디렉터리. 사용자가 자연어로 요청하면 LLM(OpenAI, Claude, Ollama 등)이 PyQGIS 코드를 생성하고 QGIS 내에서 즉시 실행하는 플러그인이다. QGIS 3.16 이상에서 동작하며 PyQt5 기반 팝업 다이얼로그 UI를 제공한다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | QGIS 플러그인 진입점. `classFactory(iface)`가 `QgisAiAutoCoder` 인스턴스를 반환 |
| `plugin_main.py` | 메인 플러그인 클래스 `QgisAiAutoCoder`. GUI 초기화, 설정 저장/로드, 메시지 처리, 비동기 API 호출, 코드 실행 오케스트레이션 담당 |
| `ui_dialog.py` | 모든 PyQt5 UI 컴포넌트 정의. `AiAutoCoderDialog`, `ChatPanel`, `SettingsPanel`, `ChatWidget`, `CodeEditorWidget`, `LogWidget`, `Card` 등 |
| `metadata.txt` | QGIS 플러그인 메타데이터 (이름, 버전, 최소 QGIS 버전, 태그 등) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `core/` | PyQGIS 코드 실행, QGIS 컨텍스트 수집, 프롬프트/대화 관리 (see `core/AGENTS.md`) |
| `llm_providers/` | LLM 제공자 추상화 계층. OpenAI, Claude, Ollama, OpenAI 호환 API 구현 (see `llm_providers/AGENTS.md`) |
| `workers/` | QThread 기반 비동기 API 호출 워커 (see `workers/AGENTS.md`) |
| `resources/` | 플러그인 아이콘 등 정적 리소스 (see `resources/AGENTS.md`) |

## Architecture Overview

```
User Input (ui_dialog.py)
    ↓
plugin_main.py (QgisAiAutoCoder)
    ├── core/context_builder.py  → QGIS 상태 수집
    ├── core/prompt_manager.py   → 시스템 프롬프트 + 대화 히스토리 관리
    ├── workers/api_worker.py    → 비동기 QThread로 LLM API 호출
    │       └── llm_providers/  → OpenAI / Claude / Ollama / 호환 API
    └── core/code_executor.py   → 생성된 코드 검증 및 exec() 실행
```

## Data Flow

1. 사용자가 자연어 입력 → `ChatPanel.send_requested` 시그널
2. `plugin_main._on_send_message()` 호출
3. `ContextBuilder.build_context()` → 현재 QGIS 프로젝트 정보 수집
4. `PromptManager` → 시스템 프롬프트에 컨텍스트 삽입, 메시지 히스토리 관리
5. `ApiWorker` (QThread) → LLM API 비동기 호출
6. 응답 수신 → `CodeExecutor.extract_code()` → 마크다운 제거
7. `CodeExecutor.execute()` → `exec()` 실행 (QGIS 네임스페이스 주입)
8. 실행 결과 → UI 업데이트 (성공/오류 메시지)
9. 오류 발생 + `auto_retry=True` → `PromptManager.add_error_feedback()` → 재호출

## For AI Agents

### Working In This Directory
- **진입점**: `__init__.py`의 `classFactory`에서 시작
- **설정 키 네임스페이스**: `QgisAiAutoCoder/` (QSettings 사용)
- **지원 LLM 제공자**: `"OpenAI"`, `"Claude"`, `"Ollama"`, `"OpenAI 호환"` (문자열 key)
- `plugin_main.py`에서 직접 UI 위젯을 조작하지 말고 `chat_panel`/`settings_panel` 인터페이스 메서드를 사용할 것
- `ApiWorker` 재사용 시 반드시 이전 워커가 종료되었는지 확인 (`isRunning()`)
- 무한 재시도 루프 방지: `_retry_with_error()`는 `auto_retry=False`로 설정하여 1회만 재시도

### Testing Requirements
- QGIS 3.16+ 환경에서 플러그인 로드 후 동작 확인
- `iface` 목킹 시 `QgisInterface` 인터페이스 메서드 구현 필요
- LLM API 호출 테스트는 실제 API 키 또는 Ollama 로컬 서버 필요

### Common Patterns
- 시그널/슬롯 패턴 (PyQt5 `pyqtSignal` / `connect`)
- QThread를 통한 UI 스레드 비차단 API 호출
- `QSettings`를 통한 영속적 설정 저장 (레지스트리/INI)

## Dependencies

### Internal
- 모든 하위 패키지(`core`, `llm_providers`, `workers`)는 상대 임포트 사용
- `ui_dialog.py`는 독립적 (외부 의존 없음)

### External
- `PyQt5` — UI 프레임워크 (QGIS 번들)
- `qgis.core`, `qgis.utils` — QGIS Python API (QGIS 번들)
- `requests` (선택) — HTTP 클라이언트. 없으면 `urllib` fallback
- `processing` (선택) — QGIS Processing Toolbox

<!-- MANUAL: -->
