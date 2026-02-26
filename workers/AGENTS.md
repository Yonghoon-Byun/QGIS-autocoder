<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-25 | Updated: 2026-02-25 -->

# workers/

## Purpose
PyQt5의 `QThread`를 기반으로 LLM API 호출을 비동기 처리하는 패키지. UI 스레드(메인 스레드)를 차단하지 않고 LLM 요청/응답을 처리하며, 시그널/슬롯 메커니즘으로 결과를 UI에 안전하게 전달한다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 (비어있음) |
| `api_worker.py` | `ApiWorker(QThread)` 클래스. LLM 제공자를 받아 백그라운드 스레드에서 `generate()` 호출 |

## ApiWorker Signals

| 시그널 | 타입 | 발생 시점 |
|--------|------|---------|
| `started_signal` | `pyqtSignal()` | `run()` 진입 직후 |
| `response_received` | `pyqtSignal(str)` | LLM 응답 수신 성공 시 |
| `error_occurred` | `pyqtSignal(str)` | 예외 발생 또는 설정 무효 시 |
| `finished_signal` | `pyqtSignal()` | 성공/실패/취소 관계없이 항상 마지막에 |

## For AI Agents

### Working In This Directory

**올바른 사용 패턴**
```python
# 1. 이전 워커 정리 확인
if self.api_worker and self.api_worker.isRunning():
    self.api_worker.cancel()
    self.api_worker.wait(3000)

# 2. 새 워커 생성 및 설정
self.api_worker = ApiWorker()
self.api_worker.setup(
    provider=self.provider,
    messages=self.prompt_manager.get_messages(),
    system_prompt=self.prompt_manager.get_system_prompt()
)

# 3. 시그널 연결
self.api_worker.response_received.connect(self._on_response)
self.api_worker.error_occurred.connect(self._on_error)
self.api_worker.finished_signal.connect(lambda: self.set_loading(False))

# 4. 시작
self.api_worker.start()
```

**취소 처리**
- `cancel()`: `_is_cancelled = True` 플래그 설정 (즉시 중단 아님)
- `run()` 내 여러 체크포인트에서 `_is_cancelled` 확인
- API 호출 중 취소 시 응답이 와도 `response_received` 시그널 미발생
- `finished_signal`은 취소 시에도 항상 발생 (UI 로딩 상태 해제 보장)

**주의사항**
- `setup()`은 `start()` 전에 반드시 호출
- `QThread`는 재사용 불가 — 매 요청마다 새 인스턴스 생성
- `finished_signal` 연결 없으면 로딩 스피너가 영구적으로 표시될 수 있음
- 시그널 콜백에서 UI 조작은 메인 스레드에서 안전 (Qt 시그널/슬롯 보장)

### Testing Requirements
- 실제 네트워크 호출 없이 테스트하려면 `provider.generate` mock 필요
- 취소 동작 테스트: `start()` 직후 `cancel()` 호출 후 시그널 발생 여부 확인

### Common Patterns
- 단발성 요청: 매번 새 `ApiWorker` 인스턴스 생성
- `finished_signal`로 항상 UI 상태 복원 (로딩 해제 등)

## Dependencies

### Internal
- `llm_providers/` — `BaseLLMProvider.generate()` 및 `validate_config()` 호출
- `plugin_main.py` — `ApiWorker`를 생성하고 시그널 연결

### External
- `PyQt5.QtCore.QThread`, `pyqtSignal` — QGIS 번들

<!-- MANUAL: -->
