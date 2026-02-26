<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-25 | Updated: 2026-02-25 -->

# core/

## Purpose
플러그인의 핵심 비즈니스 로직을 담당하는 패키지. QGIS 프로젝트 컨텍스트 수집, LLM 프롬프트 및 대화 히스토리 관리, LLM이 생성한 PyQGIS 코드의 검증 및 실행을 처리한다. UI나 네트워크 코드를 포함하지 않으며 순수 로직만 담당한다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 (비어있음) |
| `context_builder.py` | `ContextBuilder` 클래스. 현재 QGIS 프로젝트 상태(레이어 목록, CRS, 맵 범위, 활성 레이어 등)를 문자열로 수집하여 LLM 프롬프트에 주입 |
| `prompt_manager.py` | `PromptManager` 클래스. 시스템 프롬프트 템플릿 관리, 대화 히스토리 축적, 에러 피드백 메시지 생성 |
| `code_executor.py` | `CodeExecutor` 클래스. LLM 응답에서 Python 코드 추출(마크다운 제거), 문법 검증(`compile()`), QGIS 네임스페이스 주입 후 `exec()` 실행 |

## For AI Agents

### Working In This Directory

**ContextBuilder**
- `build_context()`: 호출할 때마다 현재 QGIS 상태를 새로 읽음 (캐싱 없음)
- `iface` 의존: QGIS 환경 없이는 동작 불가. 테스트 시 mock 필요
- `get_processing_algorithms()`: Processing Toolbox 전체 알고리즘 목록 반환 (느릴 수 있음)

**PromptManager**
- `SYSTEM_PROMPT_TEMPLATE`의 `{context}` 자리에 `ContextBuilder.build_context()` 결과 삽입
- 메시지 히스토리는 `[{"role": "user/assistant", "content": "..."}]` 형식
- `add_error_feedback(error)`: 에러를 user 메시지로 추가하여 자동 재시도 흐름 구현
- `clear_history()` 후에도 context는 유지됨

**CodeExecutor**
- `extract_code()`: 마크다운 ` ```python ``` ` 블록 제거. 코드 블록 없으면 원문 반환
- `execute()`: stdout/stderr를 `StringIO`로 캡처. 실행 후 반드시 복원됨
- `_build_exec_globals()`: QGIS 핵심 클래스 30개 이상을 네임스페이스에 주입
  - 항상 주입: `iface`, `__builtins__`
  - 조건부 주입 (ImportError 무시): `qgis.core.*`, `processing`, `PyQt5.*`
- `_format_exception()`: traceback에서 `exec()`/`code_executor.py` 관련 내부 라인 필터링

### Testing Requirements
- `ContextBuilder` 테스트: `iface`, `QgsProject` mock 필요
- `CodeExecutor` 테스트: 간단한 `print("hello")` 코드로 stdout 캡처 검증
- `PromptManager` 테스트: QGIS 의존성 없음, 순수 Python으로 테스트 가능

### Common Patterns
```python
# 컨텍스트 수집 → 프롬프트 설정 → 메시지 추가 순서 준수
context = context_builder.build_context()
prompt_manager.set_context(context)
prompt_manager.add_user_message(user_input)
messages = prompt_manager.get_messages()
system_prompt = prompt_manager.get_system_prompt()

# 코드 실행 결과 처리
success, stdout, stderr = code_executor.execute(code)
if not success:
    prompt_manager.add_error_feedback(stderr)
```

## Dependencies

### Internal
- `plugin_main.py`가 이 패키지의 모든 클래스를 직접 인스턴스화

### External
- `qgis.core` — `QgsProject`, `QgsWkbTypes`, `QgsMapLayerType` 등 (런타임 임포트)
- `sys`, `re`, `traceback`, `io.StringIO` — 표준 라이브러리

<!-- MANUAL: -->
