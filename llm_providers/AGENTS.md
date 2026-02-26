<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-25 | Updated: 2026-02-25 -->

# llm_providers/

## Purpose
다양한 LLM API와의 연동을 추상화한 패키지. `BaseLLMProvider` 추상 클래스를 기반으로 OpenAI, Claude(Anthropic), Ollama(로컬), OpenAI 호환 API(LM Studio, LocalAI 등) 4개의 구체적인 제공자를 구현한다. 모든 제공자는 `requests` 라이브러리 우선, 없으면 `urllib` fallback 방식으로 HTTP 통신한다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 4개 제공자 클래스 export (`BaseLLMProvider`, `OpenAIProvider`, `ClaudeProvider`, `OllamaProvider`, `OpenAICompatProvider`) |
| `base_provider.py` | `BaseLLMProvider` 추상 클래스와 `LLMProviderError` 예외 클래스 정의 |
| `openai_provider.py` | OpenAI Chat Completions API (`gpt-4o`, `gpt-4o-mini` 등). `temperature=0.1` 고정 |
| `claude_provider.py` | Anthropic Messages API (`claude-sonnet-4-20250514` 등). system 필드 별도 처리 |
| `ollama_provider.py` | 로컬 Ollama 서버 API (`/api/chat`). 서버 연결 확인 포함. timeout=300s |
| `openai_compat_provider.py` | OpenAI 호환 API (LM Studio, LocalAI 등). base_url 필수. API 키 선택사항 |

## Provider Comparison

| 제공자 | 클래스 | API 키 필요 | 기본 URL | 인증 방식 |
|--------|--------|------------|---------|---------|
| OpenAI | `OpenAIProvider` | 필수 (`sk-`) | `api.openai.com/v1` | Bearer 토큰 |
| Claude | `ClaudeProvider` | 필수 (`sk-ant-`) | `api.anthropic.com/v1` | `x-api-key` 헤더 |
| Ollama | `OllamaProvider` | 불필요 | `localhost:11434` | 없음 |
| OpenAI 호환 | `OpenAICompatProvider` | 선택 | 사용자 지정 필수 | Bearer 토큰(선택) |

## For AI Agents

### Working In This Directory

**새 제공자 추가 시**
1. `BaseLLMProvider`를 상속하여 3개 추상 메서드 구현:
   - `generate(messages, system_prompt)` → `str`
   - `get_provider_name()` → `str`
   - `get_available_models()` → `List[str]`
2. `validate_config()` 오버라이드 (필요시)
3. `__init__.py`의 `__all__`에 추가
4. `plugin_main.py`의 `provider_map` 딕셔너리에 추가
5. `ui_dialog.py`의 `SettingsPanel.provider_combo` 항목과 `_update_model_list()` 업데이트

**BaseLLMProvider 계약**
```python
# validate_config() 반환 형식
(True, "")          # 유효
(False, "오류 메시지")  # 무효

# generate() 반환: 순수 텍스트 (마크다운 포함 가능, CodeExecutor가 처리)
# generate() 예외: LLMProviderError 발생
```

**Claude Provider 특이사항**
- OpenAI와 달리 system 프롬프트를 `messages` 배열이 아닌 별도 `system` 필드로 전달
- API 버전 헤더: `anthropic-version: 2023-06-01`
- 응답 형식: `content[0].text` (OpenAI의 `choices[0].message.content`와 다름)

**Ollama Provider 특이사항**
- `validate_config()`에서 서버 연결 실제 확인 (네트워크 요청 발생)
- `get_available_models()`도 서버 API 호출 (`/api/tags`)
- timeout=300s (로컬 모델 추론 시간 고려)

### Testing Requirements
- Unit 테스트: `requests` 또는 `urllib` mock 필요
- Integration 테스트: 실제 API 키 또는 로컬 Ollama 서버 필요
- `validate_config()` 테스트: API 키 형식 검증 로직 확인

### Common Patterns
```python
# 제공자 인스턴스화 패턴 (plugin_main.py 참조)
provider = ClaudeProvider(api_key="sk-ant-...", model="claude-sonnet-4-20250514")
valid, error = provider.validate_config()
if valid:
    response = provider.generate(messages, system_prompt)
```

## Dependencies

### Internal
- `plugin_main.py`가 `provider_map`을 통해 동적으로 선택/인스턴스화

### External
- `requests` (선택) — HTTP 클라이언트. pip 설치 필요
- `urllib` — requests 없을 때 fallback (Python 표준 라이브러리)
- `json` — 표준 라이브러리

<!-- MANUAL: -->
