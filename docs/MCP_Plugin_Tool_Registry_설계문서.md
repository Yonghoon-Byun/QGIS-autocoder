# MCP 플러그인 도구 레지스트리 설계문서

**버전:** 1.0
**작성일:** 2026-02-27
**프로젝트:** QGIS-autocoder MCP Plugin Tool Registry
**상태:** 설계 완료, 구현 대기

---

## 목차

1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [핵심 컴포넌트 상세](#3-핵심-컴포넌트-상세)
4. [플러그인 연동 대상](#4-플러그인-연동-대상)
5. [도구 호출 인터페이스](#5-도구-호출-인터페이스)
6. [서드파티 플러그인 연동 가이드](#6-서드파티-플러그인-연동-가이드)
7. [보안 및 제약사항](#7-보안-및-제약사항)
8. [구현 로드맵](#8-구현-로드맵)
9. [테스트 시나리오](#9-테스트-시나리오)
10. [용어집](#10-용어집)

---

## 1. 개요

### 1.1 프로젝트명 및 목적

**프로젝트명:** QGIS-autocoder MCP Plugin Tool Registry
**버전:** 1.0.0
**목적:**

QGIS-autocoder 플러그인이 다른 QGIS 플러그인의 기능을 도구(tools)로 등록하고, LLM(Large Language Model)이 자연어 요청을 받아 이러한 도구를 자동으로 발견하고 호출할 수 있는 인프라를 제공합니다. 외부 MCP 서버 프로세스 없이 QGIS Python 환경 내에서 완전히 독립적으로 작동합니다.

### 1.2 배경 및 필요성

QGIS-autocoder는 사용자의 자연어 명령을 PyQGIS 코드로 변환하여 실행하는 플러그인입니다. 현재 아키텍처는 QGIS 기본 API만 사용할 수 있으며, 다른 플러그인의 고급 기능(예: 데이터베이스 층 로드, 도면 생성)을 활용할 수 없습니다.

**문제점:**
- 플러그인 간 통합 부족으로 사용자가 LLM을 통해 다른 플러그인 기능을 자동화할 수 없음
- 각 플러그인을 별도로 수동 조작해야 함

**해결책:**
- 플러그인 도구 레지스트리 시스템 구축
- LLM이 등록된 도구를 발견하고 호출할 수 있는 메커니즘 제공
- 기존 기능과 완벽하게 호환되는 확장 아키텍처

### 1.3 문서 범위

이 설계문서는 다음을 포함합니다:
- 전체 시스템 아키텍처 및 설계 원칙
- 새로운 컴포넌트(tool_schema.py, tool_registry.py) 상세 설명
- 기존 컴포넌트 수정사항
- 타겟 플러그인 연동 방식 (gis_layer_loader, BasePlan)
- 서드파티 플러그인 등록 방법
- 보안, 테스트, 구현 순서

---

## 2. 시스템 아키텍처

### 2.1 전체 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                       QGIS Environment                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │ gis_layer_loader     │    │  BasePlan_opt        │ (Plugin)  │
│  │  - RegionSelector    │    │  - PlanMapController │           │
│  │  - DB Functions      │    │  - WMS Integration   │           │
│  └──────┬───────────────┘    └──────┬───────────────┘           │
│         │                            │                            │
│         │ mcp_tools() or register()  │ mcp_tools() or register() │
│         │                            │                            │
│         └────────────┬───────────────┘                            │
│                      │                                             │
│         ┌────────────▼──────────────┐                             │
│         │   ToolRegistry (Singleton)│                             │
│         │                           │                             │
│         │ - _tools: Dict            │                             │
│         │ - _plugins: Dict          │                             │
│         │ - register()              │                             │
│         │ - call()                  │                             │
│         │ - scan_adapters()         │                             │
│         │ - scan_qgis_plugins()     │                             │
│         └────────────┬──────────────┘                             │
│                      │                                             │
│  ┌──────────────────▼──────────────────┐                         │
│  │      QGIS-autocoder Plugin          │                         │
│  ├──────────────────────────────────────┤                         │
│  │ UI Dialog (Chat Panel)               │                         │
│  │                                      │                         │
│  │ PromptManager                        │                         │
│  │  - SYSTEM_PROMPT_TEMPLATE            │                         │
│  │  - set_tools_prompt()                │                         │
│  │  - get_system_prompt()               │                         │
│  │    (uses string.Template)            │                         │
│  │                                      │                         │
│  │ ContextBuilder                       │                         │
│  │  - Collect QGIS context             │                         │
│  │  - Add tool summary                 │                         │
│  │                                      │                         │
│  │ CodeExecutor                         │                         │
│  │  - Extract code from LLM            │                         │
│  │  - Inject 'tools' object            │                         │
│  │  - Execute via exec()               │                         │
│  │  - Capture stdout (ToolResult)      │                         │
│  │                                      │                         │
│  │ ApiWorker (QThread)                  │                         │
│  │  - Async LLM calls                  │                         │
│  └──────────────────────────────────────┘                         │
│         ▲              ▲         ▲                                 │
│         │ system prompt│         │ tool results                   │
│         └──────────────┴─────────┘                                │
│                                                                    │
│  ┌────────────────────────┐                                       │
│  │  LLM (OpenAI/Claude/...)│                                      │
│  │                        │                                       │
│  │  Generate Python code: │                                       │
│  │  result = tools.call(  │                                       │
│  │    "plugin.tool",      │                                       │
│  │    param1=value1)      │                                       │
│  │  print(result)         │                                       │
│  └────────────────────────┘                                       │
│                                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 설계 원칙

| 원칙 | 설명 |
|------|------|
| **인-프로세스 (In-Process)** | 외부 MCP 서버 없이 QGIS Python 환경 내에서 완전히 작동 |
| **역호환성 (Backward Compatible)** | 기존 chat/code-gen/execute 플로우 완전히 보존 |
| **선택적 도구 (Optional Tools)** | 플러그인이 없어도 autocoder 정상 작동 |
| **동기 호출 (Synchronous Invocation)** | LLM 코드 관점에서 도구 호출은 동기적, 내부 비동기 처리 |
| **자동 결과 표시 (Auto-Print Results)** | ToolResult는 자동으로 print되어 채팅 패널에 표시됨 |
| **명확한 에러 처리 (Clear Error Handling)** | 도구 호출 실패 시 명확한 오류 메시지 반환 |
| **플러그인 무관 (Plugin-Agnostic)** | 핵심 모듈에 특정 플러그인 참조 없음 |

### 2.3 데이터 흐름

```
1. 사용자 자연어 요청 입력
   "서울특별시 강남구의 건축물정보 레이어를 로드해줘"
                  ↓
2. PromptManager.get_system_prompt() 호출
   ├─ $context: QGIS 프로젝트 상태 (레이어, CRS, 범위 등)
   └─ $tools: ToolRegistry.generate_tools_prompt()
              (등록된 도구 정의 및 사용 예시)
                  ↓
3. LLM API 호출 (OpenAI/Claude/Ollama)
   - System prompt + conversation history 전송
   - LLM이 Python 코드 생성:

     region_code = "11680"  # 강남구
     result = tools.call(
         "gis_layer_loader.load_db_layer",
         layer_name="건축물정보",
         region_code=region_code
     )
     print(result)
                  ↓
4. CodeExecutor.execute(code) 호출
   ├─ Code snippet 추출 (```python 블록 파싱)
   ├─ exec namespace 구성:
   │  ├─ QGIS/PyQt 기본 모듈 (qgis.core, PyQt5 등)
   │  ├─ tools = ToolRegistry instance
   │  └─ ToolResult class
   ├─ exec(code, exec_globals) 실행
   └─ stdout 캡처
                  ↓
5. tools.call() 실행
   ├─ ToolRegistry에서 "gis_layer_loader.load_db_layer" 조회
   ├─ 파라미터 검증
   │  ├─ 필수 파라미터 확인
   │  ├─ enum 값 검증
   │  └─ 기본값 적용
   ├─ Handler 함수 호출 (gis_layer_loader_adapter)
   │  ├─ PostgreSQL 연결
   │  ├─ DB 함수 호출: SELECT * FROM building_info_filter('11680')
   │  ├─ QgsVectorLayer 생성
   │  └─ QgsProject.instance()에 추가
   ├─ ToolResult(success=True, data={...}) 반환
   └─ print(result) 자동 실행 (보이기 보장)
                  ↓
6. 결과 채팅 패널에 표시
   "[성공] 건축물정보 레이어 로드 완료 (피처 수: 1234)"
```

### 2.4 컴포넌트 관계도

```
┌─────────────────────────────────────────────────────────────┐
│                   ToolRegistry (Core)                       │
│                                                             │
│  - register(ToolDefinition)                                │
│  - call(name, **kwargs) -> ToolResult                      │
│  - generate_tools_prompt() -> str                          │
│  - scan_adapters(iface) -> int                             │
│  - scan_qgis_plugins(iface) -> int                         │
└─────────────────────────────────────────────────────────────┘
         ▲           ▲           ▲           ▲
         │           │           │           │
    ┌────┴────┐  ┌───┴────┐  ┌──┴──────┐  ┌─┴────┐
    │CodeExec │  │Prompt  │  │Adapter  │  │Plugin│
    │ utor    │  │Manager │  │(GIS LL) │  │Main  │
    └────┬────┘  └───┬────┘  └──┬──────┘  └─┬────┘
         │           │          │          │
         └─────────┬─────────┬──┘──────────┘
                   │         │
           Injection  Query & Update
           of 'tools' Tool definitions
```

---

## 3. 핵심 컴포넌트 상세

### 3.1 도구 스키마 (tool_schema.py)

#### 3.1.1 목적 및 책임

도구 정의를 위한 데이터 구조와 검증을 제공합니다.

#### 3.1.2 주요 클래스

**ParameterDef** - 도구 파라미터 정의

```python
@dataclass
class ParameterDef:
    """도구 파라미터 정의."""
    type: str                           # "string", "int", "float", "bool", "list"
    description: str                    # 한국어 설명 (LLM용)
    required: bool = True               # 필수 여부
    default: Any = None                 # 필수 아님일 때 기본값
    enum: Optional[List[Any]] = None    # 허용 값 제약 (선택사항)
```

**속성:**
- `type`: 파라미터 타입 (LLM 및 검증용)
- `description`: 한국어로 된 파라미터 설명 (LLM 프롬프트에 포함)
- `required`: True이면 필수, False이면 선택사항
- `default`: 선택사항 파라미터의 기본값
- `enum`: 값 범위 제약 (예: `["horizontal", "vertical"]`)

**ToolResult** - 도구 호출 결과

```python
@dataclass
class ToolResult:
    """도구 호출 결과."""
    success: bool                       # 성공 여부
    data: Any = None                    # 반환된 구조화된 데이터
    error: str = ""                     # 실패 메시지
    message: str = ""                   # 사용자 친화적 메시지

    def __str__(self) -> str:
        """자동으로 채팅 패널에 출력되는 형식."""
        if self.success:
            return f"[성공] {self.message}" if self.message else f"[성공] {self.data}"
        return f"[실패] {self.error}"
```

**속성:**
- `success`: True/False 플래그
- `data`: 구조화된 반환값 (dict, list, 등)
- `error`: 실패 시 오류 메시지
- `message`: 사용자에게 보여줄 메시지

**ToolDefinition** - 완전한 도구 정의

```python
@dataclass
class ToolDefinition:
    """도구 레지스트리에 등록되는 완전한 도구 정의."""
    name: str                           # "gis_layer_loader.load_db_layer"
    description: str                    # 한국어 설명
    parameters: Dict[str, ParameterDef] # 파라미터명 -> 정의
    handler: Callable                   # 실제 호출되는 함수/메서드
    plugin_name: str                    # "gis_layer_loader"
    returns: str = ""                   # 반환값 설명
    examples: List[str] = field(default_factory=list)  # 사용 예시

    def to_prompt_text(self) -> str:
        """시스템 프롬프트용 한국어 문서 생성."""
        # 예:
        # ### gis_layer_loader.load_db_layer
        # PostgreSQL 데이터베이스에서 지역 레이어를 로드합니다.
        # Parameters:
        #   - layer_name (string) (필수): 로드할 레이어 이름
        #   - region_code (string) (필수): 행정 코드
        # Returns: ToolResult with layer name and feature count
        # Examples:
        #   result = tools.call("gis_layer_loader.load_db_layer", ...)
```

**메서드:**
- `to_prompt_text()`: 시스템 프롬프트에 포함될 한국어 텍스트 생성

#### 3.1.3 입출력 데이터 구조

**입력 (도구 정의 시):**
```python
tool = ToolDefinition(
    name="gis_layer_loader.load_db_layer",
    description="PostgreSQL에서 지역 레이어를 로드합니다.",
    parameters={
        "layer_name": ParameterDef(
            type="string",
            description="로드할 레이어 이름",
            required=True,
            enum=["건축물정보", "도로경계선", ...]
        ),
        "region_code": ParameterDef(
            type="string",
            description="행정 코드 (예: 11680)",
            required=True
        )
    },
    handler=adapter.load_db_layer,
    plugin_name="gis_layer_loader",
    returns="레이어 정보 (이름, 피처 수)",
    examples=['tools.call("gis_layer_loader.load_db_layer", layer_name="건축물정보", region_code="11680")']
)
```

**출력 (도구 호출 결과):**
```python
result = ToolResult(
    success=True,
    data={
        "layer_name": "건축물정보",
        "feature_count": 1234,
        "crs": "EPSG:5179"
    },
    message="건축물정보 레이어 로드 완료"
)
# str(result) -> "[성공] 건축물정보 레이어 로드 완료"
```

#### 3.1.4 의존성

- Python 표준 라이브러리만 사용 (dataclasses, typing)
- 외부 의존성 없음

---

### 3.2 도구 레지스트리 (tool_registry.py)

#### 3.2.1 목적 및 책임

중앙 단일 인스턴스(Singleton)로서 도구 등록, 발견, 호출을 관리합니다.

#### 3.2.2 싱글톤 인스턴스

QGIS-autocoder 플러그인이 `__init__`에서 하나의 ToolRegistry 인스턴스를 생성하여 유지합니다.

```python
# plugin_main.py에서
class QgisAiAutoCoder:
    def __init__(self, iface):
        self.tool_registry = ToolRegistry()  # 전역 싱글톤
        self.code_executor = CodeExecutor(iface, tool_registry=self.tool_registry)
```

#### 3.2.3 핵심 메서드

**등록 메서드:**

```python
def register(self, tool: ToolDefinition) -> None:
    """단일 도구 등록."""
    self._tools[tool.name] = tool
    if tool.plugin_name not in self._plugins:
        self._plugins[tool.plugin_name] = []
    self._plugins[tool.plugin_name].append(tool.name)

def register_many(self, tools: List[ToolDefinition]) -> None:
    """여러 도구 한 번에 등록."""
    for tool in tools:
        self.register(tool)

def unregister_plugin(self, plugin_name: str) -> None:
    """플러그인의 모든 도구 제거."""
    if plugin_name in self._plugins:
        for tool_name in self._plugins[plugin_name]:
            self._tools.pop(tool_name, None)
        del self._plugins[plugin_name]
```

**조회 메서드:**

```python
def get_tool(self, name: str) -> Optional[ToolDefinition]:
    """도구명으로 도구 정의 조회."""
    return self._tools.get(name)

def list_tools(self) -> List[str]:
    """등록된 모든 도구명 목록."""
    return list(self._tools.keys())

def list_plugins(self) -> List[str]:
    """등록된 플러그인명 목록."""
    return list(self._plugins.keys())
```

**호출 메서드 (핵심):**

```python
def call(self, name: str, **kwargs) -> ToolResult:
    """도구 호출 및 결과 반환.

    이 메서드는 LLM이 생성한 코드에서 호출됩니다:
        result = tools.call("gis_layer_loader.load_db_layer",
                          layer_name="건축물정보",
                          region_code="11680")

    처리 단계:
    1. 도구 존재 확인
    2. 필수 파라미터 검증
    3. 기본값 적용
    4. enum 제약 검증
    5. Handler 함수 호출
    6. Exception 처리
    7. ToolResult 자동 print (채팅 가시성 보장)

    Returns:
        ToolResult: success, data, error 속성 포함
    """
    tool = self._tools.get(name)
    if not tool:
        result = ToolResult(
            success=False,
            error=f"도구 '{name}'을(를) 찾을 수 없습니다. "
                  f"사용 가능: {', '.join(self._tools.keys()) or '(없음)'}"
        )
        print(result)  # 자동 출력 보장
        return result

    # 파라미터 검증
    for pname, pdef in tool.parameters.items():
        if pdef.required and pname not in kwargs:
            result = ToolResult(
                success=False,
                error=f"필수 파라미터 '{pname}' 누락"
            )
            print(result)
            return result

    # 기본값 적용
    for pname, pdef in tool.parameters.items():
        if not pdef.required and pname not in kwargs:
            kwargs[pname] = pdef.default

    # enum 검증
    for pname, pdef in tool.parameters.items():
        if pdef.enum and pname in kwargs and kwargs[pname] not in pdef.enum:
            result = ToolResult(
                success=False,
                error=f"파라미터 '{pname}' 값 '{kwargs[pname]}'은 "
                      f"허용되지 않음. 허용값: {pdef.enum}"
            )
            print(result)
            return result

    # Handler 호출
    try:
        result = tool.handler(**kwargs)
        if isinstance(result, ToolResult):
            print(result)  # 자동 출력
            return result
        # Raw 반환값 래핑
        wrapped = ToolResult(success=True, data=result, message=str(result))
        print(wrapped)
        return wrapped
    except Exception as e:
        result = ToolResult(success=False, error=f"도구 실행 오류: {str(e)}")
        print(result)
        return result
```

**프롬프트 생성 메서드:**

```python
def generate_tools_prompt(self) -> str:
    """등록된 모든 도구를 설명하는 시스템 프롬프트 섹션 생성.

    반환값: 마크다운 형식의 도구 설명서

    예:
        ## 사용 가능한 플러그인 도구 (Plugin Tools)

        아래 도구들은 `tools.call("도구명", 파라미터=값)` 형식으로 호출할 수 있습니다.
        ...

        ### [gis_layer_loader] 플러그인

        ### gis_layer_loader.load_db_layer
        PostgreSQL에서 지역 레이어를 로드합니다.
        ...
    """
    if not self._tools:
        return ""

    sections = []
    sections.append("## 사용 가능한 플러그인 도구 (Plugin Tools)")
    sections.append("")
    sections.append("도구를 호출하려면 `tools.call(\"도구명\", param=value)` 형식을 사용하세요.")
    sections.append("도구 호출 결과를 반드시 print()로 출력하세요.")
    sections.append("")

    for plugin_name in sorted(self._plugins.keys()):
        sections.append(f"### [{plugin_name}] 플러그인")
        for tool_name in self._plugins[plugin_name]:
            tool = self._tools[tool_name]
            sections.append(tool.to_prompt_text())
            sections.append("")

    return "\n".join(sections)
```

**플러그인 스캔 메서드:**

```python
def scan_qgis_plugins(self, iface) -> int:
    """로드된 QGIS 플러그인에서 mcp_tools() 메서드 검색.

    Convention:
        - 플러그인의 main class가 mcp_tools(iface) 메서드를 구현
        - 메서드는 List[ToolDefinition]을 반환

    Returns:
        int: 발견된 도구 개수
    """
    count = 0
    try:
        from qgis.utils import plugins as qgis_plugins
        for plugin_name, plugin_instance in qgis_plugins.items():
            if hasattr(plugin_instance, 'mcp_tools'):
                try:
                    tools = plugin_instance.mcp_tools(iface)
                    if tools:
                        self.register_many(tools)
                        count += len(tools)
                except Exception as e:
                    print(f"[ToolRegistry] 플러그인 '{plugin_name}' 스캔 오류: {e}")
    except ImportError:
        pass
    return count

def scan_adapters(self, iface) -> int:
    """내장 어댑터 모듈에서 도구 정의 로드.

    자동으로 아래 어댑터들을 시도:
    - adapters.gis_layer_loader_adapter.get_tools(iface)
    - adapters.base_plan_adapter.get_tools(iface)

    Returns:
        int: 발견된 도구 개수
    """
    count = 0
    adapter_modules = []

    try:
        from ..adapters.gis_layer_loader_adapter import get_tools
        adapter_modules.append(("gis_layer_loader_adapter", get_tools))
    except (ImportError, Exception):
        pass

    try:
        from ..adapters.base_plan_adapter import get_tools
        adapter_modules.append(("base_plan_adapter", get_tools))
    except (ImportError, Exception):
        pass

    for adapter_name, get_tools_fn in adapter_modules:
        try:
            tools = get_tools_fn(iface)
            if tools:
                self.register_many(tools)
                count += len(tools)
        except Exception as e:
            print(f"[ToolRegistry] 어댑터 '{adapter_name}' 로드 오류: {e}")

    return count
```

#### 3.2.4 내부 데이터 구조

```python
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}      # name -> ToolDefinition
        self._plugins: Dict[str, List[str]] = {}         # plugin_name -> [tool names]
```

**_tools:** 도구명(예: "gis_layer_loader.load_db_layer")을 key로 하는 딕셔너리
**_plugins:** 플러그인명(예: "gis_layer_loader")을 key로 하는 딕셔너리, 값은 해당 플러그인이 제공하는 도구명 리스트

#### 3.2.5 의존성

- `tool_schema` (같은 core 패키지)
- QGIS API (scan_qgis_plugins에서만, 선택적)

---

### 3.3 어댑터 계층 (adapters/)

#### 3.3.1 목적

QGIS 플러그인의 기능을 ToolDefinition 객체로 래핑하여 ToolRegistry와 호환되게 만듭니다.

#### 3.3.2 공통 구조

모든 어댑터는 다음 함수를 제공합니다:

```python
def get_tools(iface: QgisInterface) -> List[ToolDefinition]:
    """플러그인의 도구 정의를 반환합니다.

    Args:
        iface: QGIS 인터페이스

    Returns:
        List[ToolDefinition]: 도구 정의 리스트

    Note:
        - 플러그인이 설치되지 않았으면 빈 리스트 반환
        - 오류 발생 시 예외 발생 (ToolRegistry에서 처리)
    """
```

#### 3.3.3 gis_layer_loader_adapter.py

**역할:** gis_layer_loader 플러그인을 MCP 도구로 어댑트

**제공 도구:**

| 도구 | 설명 | 파라미터 |
|------|------|---------|
| `gis_layer_loader.list_available_layers` | 사용 가능한 레이어 목록 | (없음) |
| `gis_layer_loader.list_regions` | 행정 지역 목록 | level, parent_code |
| `gis_layer_loader.load_db_layer` | DB 레이어 로드 | layer_name, region_code |
| `gis_layer_loader.get_region_code` | 지역명으로 코드 조회 | sido, sigungu, emd |

**핵심 데이터 (플러그인에서 추출):**

```python
DB_HOST = "geo-spatial-hub.postgres.database.azure.com"
DB_PORT = "6432"
DB_NAME = "dde-water"
DB_SCHEMA = "public"
DB_USER = "waterviewer"
DB_PASSWORD = "dohwaviewer"

AVAILABLE_LAYERS = [
    {"name": "건축물정보", "function_name": "building_info_filter"},
    {"name": "도로경계선", "function_name": "road_outline_clip"},
    # ... 16개 레이어
]
```

**주요 구현 포인트:**

1. PostgreSQL 연결 (psycopg2)
2. 서버 측 함수 호출: `SELECT * FROM public.{function_name}('{region_code}')`
3. QgsVectorLayer/QgsRasterLayer 생성 및 추가
4. admin_regions.csv 파싱 (BOM-UTF8 인코딩)

#### 3.3.4 base_plan_adapter.py

**역할:** BasePlan_opt 플러그인을 MCP 도구로 어댑트

**제공 도구:**

| 도구 | 설명 | 파라미터 |
|------|------|---------|
| `base_plan.load_target_area` | 대상 영역(Area A) 로드 | admin_code |
| `base_plan.set_drawing_extent` | 도면 범위(A0) 설정 | orientation |
| `base_plan.load_drawing_area` | 도면 영역(Area B) 로드 | (없음) |
| `base_plan.add_overlay` | 오버레이 추가 | overlay_type |
| `base_plan.export` | PDF/이미지 내보내기 | format |
| `base_plan.full_reset` | 전체 상태 초기화 | (없음) |

**핵심 위임:**

```python
plugin = qgis.utils.plugins.get("BasePlan_opt")
controller = plugin.controller  # PlanMapController 인스턴스

# 메서드 위임
controller.on_admin_selected(admin_code)
controller.set_box_horizontal()
controller.load_area_b()
controller.finalize()
controller.export_pdf()
```

**주요 구현 포인트:**

1. BasePlan_opt 플러그인 존재 확인
2. PlanMapController 인스턴스 확인 (없으면 plugin.run() 호출)
3. 상태 검증 (예: export 전에 finalize 확인)

---

### 3.4 기존 파일 수정사항

#### 3.4.1 core/prompt_manager.py

**문제 (Fix 1 - CRITICAL):**

기존 코드는 `str.format()`을 사용하는데, 템플릿에 literal 중괄호가 많아서 `{tools}` 추가 시 오류 발생:

```python
# 기존 (오류 발생)
SYSTEM_PROMPT_TEMPLATE = """...
result = processing.run("native:buffer", {
    'INPUT': layer,
    'DISTANCE': 100,
    ...
})
...
"""

def get_system_prompt(self) -> str:
    return self.SYSTEM_PROMPT_TEMPLATE.format(context=self.context)  # ValueError!
```

**해결책:**

`string.Template` 사용 (달러 기호 기반, 중괄호 무시):

```python
import string

class PromptManager:
    SYSTEM_PROMPT_TEMPLATE = """...
$context

$tools

## 출력 형식
..."""

    def __init__(self):
        self.context = ""
        self.tools_prompt = ""

    def set_tools_prompt(self, text: str):
        self.tools_prompt = text

    def get_system_prompt(self) -> str:
        template = string.Template(self.SYSTEM_PROMPT_TEMPLATE)
        return template.safe_substitute(
            context=self.context,
            tools=self.tools_prompt
        )
```

**변경 내용:**

| 변경 | 위치 | 상세 |
|------|------|------|
| Import 추가 | 상단 | `import string` |
| 템플릿 수정 | SYSTEM_PROMPT_TEMPLATE | `{context}` → `$context`, `{tools}` 추가 |
| 초기화 추가 | `__init__` | `self.tools_prompt = ""` |
| 메서드 추가 | `set_tools_prompt()` | 도구 프롬프트 업데이트 메서드 |
| 메서드 수정 | `get_system_prompt()` | `string.Template.safe_substitute()` 사용 |

**역호환성:** ✓ 완벽 보존
- 기존 호출 코드 수정 불필요
- 도구 없을 때 `$tools`는 빈 문자열로 대체됨

#### 3.4.2 core/code_executor.py

**목적:** `tools` 객체를 exec namespace에 주입

**변경 내용:**

```python
class CodeExecutor:
    def __init__(self, iface, tool_registry=None):
        self.iface = iface
        self.tool_registry = tool_registry  # 추가

    def _build_exec_globals(self):
        """exec namespace 구성."""
        exec_globals = {
            # 기존 QGIS/PyQt 모듈들...
        }

        # 도구 주입 (도구 레지스트리 있을 때만)
        if self.tool_registry:
            from .tool_schema import ToolResult
            exec_globals['tools'] = self.tool_registry
            exec_globals['ToolResult'] = ToolResult

        return exec_globals
```

**변경 내용:**

| 변경 | 위치 | 상세 |
|------|------|------|
| 파라미터 추가 | `__init__` | `tool_registry=None` |
| 저장 | `__init__` | `self.tool_registry = tool_registry` |
| 주입 | `_build_exec_globals()` | `tools` 및 `ToolResult` 추가 |

**역호환성:** ✓ 완벽 보존
- `tool_registry=None`이 기본값이므로 기존 호출 코드 수정 불필요
- 도구 없으면 이전과 동일하게 작동

#### 3.4.3 core/context_builder.py

**목적:** 컨텍스트에 도구 요약 추가 (선택사항)

**추가 메서드:**

```python
class ContextBuilder:
    def __init__(self, iface, tool_registry=None):
        # ... 기존 코드
        self.tool_registry = tool_registry

    def get_tool_summary(self) -> str:
        """컨텍스트에 포함될 도구 요약.

        Returns:
            str: 간단한 도구 목록 (예: 사용 가능한 도구 5개)
        """
        if not self.tool_registry:
            return ""

        tools = self.tool_registry.list_tools()
        plugins = self.tool_registry.list_plugins()

        if not tools:
            return ""

        return f"사용 가능한 MCP 도구: {len(tools)}개 ({', '.join(plugins)})"
```

#### 3.4.4 plugin_main.py

**목적:** ToolRegistry 초기화 및 스캔, 프롬프트 업데이트

**변경 내용:**

```python
class QgisAiAutoCoder:
    def __init__(self, iface):
        self.iface = iface
        self.tool_registry = ToolRegistry()  # 추가
        self.code_executor = CodeExecutor(iface, tool_registry=self.tool_registry)  # 전달
        # ... 기존 초기화

    def initGui(self):
        # ... 기존 UI 설정
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, self._scan_plugin_tools)  # 지연 스캔

    def _scan_plugin_tools(self):
        """플러그인 도구 스캔 (모든 플러그인 로드 후)."""
        count = self.tool_registry.scan_adapters(self.iface)
        count += self.tool_registry.scan_qgis_plugins(self.iface)
        if count > 0:
            print(f"[QgisAiAutoCoder] {count}개 MCP 도구 발견")

    def _on_send_message(self):
        """메시지 전송 (LLM 호출 전)."""
        # ... 기존 코드

        # 도구 프롬프트 업데이트 (새로 추가)
        tools_prompt = self.tool_registry.generate_tools_prompt()
        self.prompt_manager.set_tools_prompt(tools_prompt)

        # ... LLM 호출

    def get_tool_registry(self) -> ToolRegistry:
        """외부 플러그인용 공개 API."""
        return self.tool_registry

    def unload(self):
        """플러그인 언로드."""
        # tool_registry는 Python 객체이므로 특별한 정리 불필요
        pass
```

**변경 내용:**

| 변경 | 위치 | 상세 |
|------|------|------|
| Import 추가 | 상단 | `from .core.tool_registry import ToolRegistry` |
| 인스턴스 생성 | `__init__` | `self.tool_registry = ToolRegistry()` |
| CodeExecutor 수정 | `__init__` | `tool_registry=self.tool_registry` 전달 |
| 스캔 추가 | `initGui` | `QTimer.singleShot(0, self._scan_plugin_tools)` |
| 메서드 추가 | `_scan_plugin_tools()` | 어댑터/플러그인 스캔 |
| 프롬프트 업데이트 | `_on_send_message()` | 도구 프롬프트 설정 |
| 공개 API 추가 | `get_tool_registry()` | 외부 플러그인용 |

---

## 4. 플러그인 연동 대상

### 4.1 gis_layer_loader

#### 4.1.1 플러그인 정보

| 속성 | 값 |
|------|-----|
| **Zip 파일** | `plugins/gis_layer_loader.zip` |
| **모듈명** | `gis_layer_loader` |
| **메인 클래스** | `GISLayerLoaderPlugin` |
| **대화 클래스** | `RegionSelectorDialog` |
| **QGIS 레지스트리 키** | `gis_layer_loader` |
| **DB 연결** | Azure PostgreSQL (geo-spatial-hub.postgres.database.azure.com:6432) |

#### 4.1.2 기능 개요

계층적 행정 지역 선택기로, PostgreSQL 데이터베이스에서 지역별 GIS 레이어를 로드합니다.

**주요 기능:**
- CSV 기반 행정 구역 계층 탐색 (시도 → 시군구 → 읍면동)
- PostgreSQL 서버 함수 호출로 지역별 레이어 로드
- 16가지 레이어 타입 지원

#### 4.1.3 노출 도구

**도구 1: list_available_layers**

```python
ToolDefinition(
    name="gis_layer_loader.list_available_layers",
    description="사용 가능한 모든 GIS 레이어 목록을 반환합니다.",
    parameters={},
    handler=adapter._list_available_layers,
    plugin_name="gis_layer_loader",
    returns="레이어 이름과 함수명 포함한 딕셔너리 리스트",
    examples=['result = tools.call("gis_layer_loader.list_available_layers")']
)
```

**도구 2: list_regions**

```python
ToolDefinition(
    name="gis_layer_loader.list_regions",
    description="지정된 행정 레벨의 지역 목록을 반환합니다.",
    parameters={
        "level": ParameterDef(
            type="string",
            description="행정 레벨 ('sido'|'sigungu'|'emd')",
            required=True,
            enum=["sido", "sigungu", "emd"]
        ),
        "parent_code": ParameterDef(
            type="string",
            description="상위 지역 코드 (예: '11' for 서울시)",
            required=False
        )
    },
    handler=adapter._list_regions,
    plugin_name="gis_layer_loader",
    returns="{ name, code } 객체 리스트",
    examples=[
        'result = tools.call("gis_layer_loader.list_regions", level="sido")',
        'result = tools.call("gis_layer_loader.list_regions", level="sigungu", parent_code="11")'
    ]
)
```

**도구 3: load_db_layer**

```python
ToolDefinition(
    name="gis_layer_loader.load_db_layer",
    description="PostgreSQL DB에서 지역별 레이어를 로드하고 QGIS 프로젝트에 추가합니다.",
    parameters={
        "layer_name": ParameterDef(
            type="string",
            description="로드할 레이어 이름",
            required=True,
            enum=[layer["name"] for layer in AVAILABLE_LAYERS]  # 16개
        ),
        "region_code": ParameterDef(
            type="string",
            description="행정 코드 (예: '11680' = 강남구)",
            required=True
        )
    },
    handler=adapter._load_db_layer,
    plugin_name="gis_layer_loader",
    returns="{ layer_name, feature_count, crs }",
    examples=[
        'result = tools.call("gis_layer_loader.load_db_layer", '
        'layer_name="건축물정보", region_code="11680")'
    ]
)
```

**도구 4: get_region_code**

```python
ToolDefinition(
    name="gis_layer_loader.get_region_code",
    description="지역 이름으로 행정 코드를 조회합니다.",
    parameters={
        "sido": ParameterDef(
            type="string",
            description="시도명 (예: '서울특별시')",
            required=True
        ),
        "sigungu": ParameterDef(
            type="string",
            description="시군구명 (예: '강남구')",
            required=False
        ),
        "emd": ParameterDef(
            type="string",
            description="읍면동명",
            required=False
        )
    },
    handler=adapter._get_region_code,
    plugin_name="gis_layer_loader",
    returns="행정 코드 문자열",
    examples=[
        'code = tools.call("gis_layer_loader.get_region_code", sido="서울특별시", sigungu="강남구").data'
    ]
)
```

#### 4.1.4 데이터베이스 연결 정보

```python
DB_CONFIG = {
    "host": "geo-spatial-hub.postgres.database.azure.com",
    "port": 6432,
    "database": "dde-water",
    "user": "waterviewer",
    "password": "dohwaviewer",
    "schema": "public"
}

LAYER_FUNCTIONS = {
    "건축물정보": "building_info_filter",
    "도로경계선": "road_outline_clip",
    # ... 16개
}
```

#### 4.1.5 호출 흐름

```
1. LLM: "서울시 강남구 건축물정보를 로드해줘"
2. tools.call("gis_layer_loader.load_db_layer",
              layer_name="건축물정보",
              region_code="11680")
3. Adapter:
   - 파라미터 검증
   - psycopg2로 PostgreSQL 연결
   - SELECT * FROM building_info_filter('11680') 실행
   - QgsVectorLayer 생성
   - QgsProject.instance().addMapLayer(layer)
4. 반환: ToolResult(success=True, data={layer_name, feature_count, crs})
5. auto-print: "[성공] 건축물정보 레이어 로드 완료 (피처 수: 1234)"
```

---

### 4.2 BasePlan_opt

#### 4.2.1 플러그인 정보

| 속성 | 값 |
|------|-----|
| **Zip 파일** | `plugins/BasePlan.zip` |
| **모듈명** | `BasePlan_opt` |
| **메인 클래스** | `BasePlan` |
| **컨트롤러** | `PlanMapController` |
| **QGIS 레지스트리 키** | `BasePlan_opt` |
| **WMS 서버** | GeoServer (http://10.0.0.22:8080/geoserver/gis_water/wms) |

#### 4.2.2 기능 개요

토목 기본 도면 생성을 위한 프로세스 자동화:
1. 행정 코드로 대상 영역(Area A) 선택
2. A0 용지 크기로 도면 범위 설정 (가로/세로)
3. 범위 내 도면 영역(Area B) 로드
4. 오버레이 추가 (북쪽 화살표, 축척 표시)
5. PDF/이미지로 내보내기

#### 4.2.3 노출 도구

**도구 1: load_target_area**

```python
ToolDefinition(
    name="base_plan.load_target_area",
    description="행정 코드로 대상 영역(Area A)을 WMS에서 로드합니다.",
    parameters={
        "admin_code": ParameterDef(
            type="string",
            description="행정 코드 (예: '11680' = 강남구)",
            required=True
        )
    },
    handler=adapter._load_target_area,
    plugin_name="BasePlan_opt",
    returns="{ extent_xmin, extent_ymin, extent_xmax, extent_ymax }",
    examples=['tools.call("base_plan.load_target_area", admin_code="11680")']
)
```

**도구 2: set_drawing_extent**

```python
ToolDefinition(
    name="base_plan.set_drawing_extent",
    description="A0 도면 범위를 가로 또는 세로로 설정합니다.",
    parameters={
        "orientation": ParameterDef(
            type="string",
            description="방향 ('horizontal'|'vertical')",
            required=True,
            enum=["horizontal", "vertical"]
        )
    },
    handler=adapter._set_drawing_extent,
    plugin_name="BasePlan_opt",
    returns="{ bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax }",
    examples=['tools.call("base_plan.set_drawing_extent", orientation="horizontal")']
)
```

**도구 3: load_drawing_area**

```python
ToolDefinition(
    name="base_plan.load_drawing_area",
    description="현재 도면 범위(Area B) 내의 데이터를 WMS에서 로드합니다.",
    parameters={},
    handler=adapter._load_drawing_area,
    plugin_name="BasePlan_opt",
    returns="{ status, layers_loaded }",
    examples=['tools.call("base_plan.load_drawing_area")']
)
```

**도구 4: add_overlay**

```python
ToolDefinition(
    name="base_plan.add_overlay",
    description="도면에 오버레이 요소를 추가합니다.",
    parameters={
        "overlay_type": ParameterDef(
            type="string",
            description="오버레이 타입",
            required=True,
            enum=["north_arrow", "scale_bar", "outer_gradient"]
        )
    },
    handler=adapter._add_overlay,
    plugin_name="BasePlan_opt",
    returns="{ status }",
    examples=['tools.call("base_plan.add_overlay", overlay_type="north_arrow")']
)
```

**도구 5: export**

```python
ToolDefinition(
    name="base_plan.export",
    description="최종 도면을 PDF 또는 이미지로 내보냅니다.",
    parameters={
        "format": ParameterDef(
            type="string",
            description="내보내기 형식",
            required=True,
            enum=["pdf", "image"]
        )
    },
    handler=adapter._export,
    plugin_name="BasePlan_opt",
    returns="{ file_path, format }",
    examples=['tools.call("base_plan.export", format="pdf")']
)
```

**도구 6: full_reset**

```python
ToolDefinition(
    name="base_plan.full_reset",
    description="BasePlan의 모든 상태를 초기화합니다.",
    parameters={},
    handler=adapter._full_reset,
    plugin_name="BasePlan_opt",
    returns="{ status }",
    examples=['tools.call("base_plan.full_reset")']
)
```

#### 4.2.4 WMS 연결 정보

```python
WMS_CONFIG = {
    "url": "http://10.0.0.22:8080/geoserver/gis_water/wms",
    "crs": "EPSG:5179",
    "layers": {
        "hjd": {
            "layer_a": "hjd_mv_filter",
            "layer_b": "hjd_bbox"
        },
        "contour": {
            "layer_a": "contour_mv_filter",
            "layer_b": "contour_bbox"
        },
        "road": {
            "layer_a": "road_mv_filter",
            "layer_b": "road_bbox"
        }
    }
}
```

#### 4.2.5 호출 흐름

```
1. LLM: "기본도면을 만들어줘. 강남구로 설정하고 가로로 설정해줘."
2. tools.call("base_plan.load_target_area", admin_code="11680")
   - PlanMapController.on_admin_selected("11680")
   - WMS에서 Area A 로드
3. tools.call("base_plan.set_drawing_extent", orientation="horizontal")
   - PlanMapController.set_box_horizontal()
   - A0 비율로 도면 범위 설정
4. tools.call("base_plan.load_drawing_area")
   - PlanMapController.load_area_b()
   - 범위 내 데이터 로드
5. tools.call("base_plan.add_overlay", overlay_type="north_arrow")
   - PlanMapController.add_north_arrow()
6. tools.call("base_plan.export", format="pdf")
   - PlanMapController.finalize()
   - PlanMapController.export_pdf()
   - 파일 경로 반환
```

---

## 5. 도구 호출 인터페이스

### 5.1 tools.call() 기본 사용법

LLM이 생성한 코드에서 호출하는 주요 메서드:

```python
result = tools.call("도구명", param1=값1, param2=값2, ...)
```

**반환값:** `ToolResult` 객체
- `result.success`: bool (True/False)
- `result.data`: Any (반환값)
- `result.error`: str (오류 메시지)
- `result.message`: str (사용자 메시지)

### 5.2 성공 케이스

```python
# 도구 호출
result = tools.call(
    "gis_layer_loader.load_db_layer",
    layer_name="건축물정보",
    region_code="11680"
)

# result 상태
# - result.success = True
# - result.data = {"layer_name": "건축물정보", "feature_count": 1234, "crs": "EPSG:5179"}
# - result.error = ""
# - result.message = "건축물정보 레이어 로드 완료"

# 결과 확인
if result.success:
    print(f"레이어 로드: {result.data['layer_name']} ({result.data['feature_count']} 피처)")
else:
    print(f"오류: {result.error}")
```

**자동 출력:**
```
[성공] 건축물정보 레이어 로드 완료
```

### 5.3 실패 케이스

**케이스 1: 필수 파라미터 누락**
```python
result = tools.call("gis_layer_loader.load_db_layer", layer_name="건축물정보")
# result.success = False
# result.error = "필수 파라미터 'region_code'이(가) 누락되었습니다."

# 자동 출력:
# [실패] 필수 파라미터 'region_code'이(가) 누락되었습니다.
```

**케이스 2: 허용되지 않는 enum 값**
```python
result = tools.call(
    "base_plan.set_drawing_extent",
    orientation="diagonal"  # 허용값: horizontal, vertical
)
# result.success = False
# result.error = "파라미터 'orientation' 값 'diagonal'은(는) 허용되지 않습니다."
```

**케이스 3: 도구 존재하지 않음**
```python
result = tools.call("invalid.tool")
# result.success = False
# result.error = "도구 'invalid.tool'을(를) 찾을 수 없습니다. 사용 가능한 도구: ..."
```

**케이스 4: 도구 실행 중 예외**
```python
result = tools.call("gis_layer_loader.load_db_layer", ...)
# DB 연결 실패 등
# result.success = False
# result.error = "도구 실행 오류: [오류 메시지]"
```

### 5.4 tools.list_tools() (참고용)

시스템 프롬프트에는 포함되지 않지만, LLM이 호출 가능:

```python
available = tools.list_tools()
# ["gis_layer_loader.list_available_layers", "gis_layer_loader.load_db_layer", ...]
```

### 5.5 ToolResult를 변수로 사용

```python
# 도구 결과로 후속 작업 수행
result = tools.call("gis_layer_loader.get_region_code", sido="서울특별시", sigungu="강남구")
if result.success:
    region_code = result.data
    print(f"지역 코드: {region_code}")
```

---

## 6. 서드파티 플러그인 연동 가이드

### 6.1 개요

다른 QGIS 플러그인 개발자가 QGIS-autocoder와 통합하려면 두 가지 방식 중 하나를 선택할 수 있습니다.

### 6.2 방식 1: Convention 기반 (mcp_tools 메서드)

가장 간단한 방식으로, 플러그인의 메인 클래스에 `mcp_tools(iface)` 메서드를 구현합니다.

#### 6.2.1 구현 예시

```python
# your_plugin/plugin.py

from qgis_autocoder.core.tool_schema import ToolDefinition, ParameterDef, ToolResult

class YourPlugin:
    def __init__(self, iface):
        self.iface = iface

    def mcp_tools(self, iface):
        """QGIS-autocoder의 자동 스캔에서 호출됩니다.

        Returns:
            List[ToolDefinition]: 제공할 도구 목록
        """
        return [
            ToolDefinition(
                name="your_plugin.my_action",
                description="플러그인 기능을 수행합니다.",
                parameters={
                    "input_param": ParameterDef(
                        type="string",
                        description="입력 파라미터 설명",
                        required=True
                    ),
                    "optional_param": ParameterDef(
                        type="int",
                        description="선택 파라미터",
                        required=False,
                        default=10
                    )
                },
                handler=self._my_action_handler,
                plugin_name="your_plugin",
                returns="작업 결과 설명",
                examples=['tools.call("your_plugin.my_action", input_param="value")']
            )
        ]

    def _my_action_handler(self, input_param: str, optional_param: int = 10) -> ToolResult:
        """실제 도구 로직."""
        try:
            # 플러그인 로직 수행
            result_data = self._do_something(input_param, optional_param)

            return ToolResult(
                success=True,
                data=result_data,
                message=f"작업 완료: {result_data}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"작업 실패: {str(e)}"
            )

    def _do_something(self, input_param: str, optional_param: int):
        # 실제 기능 구현
        return {"status": "done", "input": input_param, "param": optional_param}
```

#### 6.2.2 주요 포인트

1. **mcp_tools() 서명:** `def mcp_tools(self, iface: QgisInterface) -> List[ToolDefinition]`
2. **Handler 서명:** 일반 Python 함수, ToolDefinition.parameters와 일치하는 파라미터
3. **반환값:**
   - ToolResult를 반환하면 그대로 사용
   - 다른 타입 반환하면 자동으로 ToolResult로 래핑
4. **에러 처리:** 예외는 자동으로 ToolResult(success=False)로 변환

### 6.3 방식 2: Direct Registration (레지스트리 호출)

플러그인이 이미 로드된 후 QGIS-autocoder 레지스트리에 직접 등록:

```python
# your_plugin의 어디서든
from qgis.utils import plugins

autocoder = plugins.get("qgis_autocoder")  # 또는 "QGIS AI Auto-Coder"
if autocoder:
    registry = autocoder.get_tool_registry()

    my_tool = ToolDefinition(...)
    registry.register(my_tool)
```

### 6.4 도구 정의 작성 체크리스트

| 항목 | 확인 |
|------|------|
| **name** | `"plugin_name.tool_name"` 형식 (영문, 소문자) |
| **description** | 한국어로 작성, 무엇을 하는지 명확 |
| **parameters** | 필수/선택 구분, enum 값 명시 |
| **handler** | 파라미터 매치, 에러 처리 |
| **plugin_name** | QGIS 플러그인 레지스트리 키와 동일 |
| **returns** | 반환값의 구조/형식 설명 |
| **examples** | LLM이 이해하기 쉬운 호출 예시 |

### 6.5 파라미터 스키마 작성 가이드

```python
# 좋은 예
ParameterDef(
    type="string",
    description="로드할 파일 경로 (절대 경로 권장)",
    required=True
)

# 좋은 예 - enum 제약
ParameterDef(
    type="string",
    description="내보내기 형식",
    required=True,
    enum=["pdf", "image", "svg"]
)

# 좋은 예 - 선택 파라미터
ParameterDef(
    type="int",
    description="버퍼 거리 (단위: 미터)",
    required=False,
    default=100
)

# 나쁜 예 - 모호한 설명
ParameterDef(type="string", description="파라미터", required=True)
```

---

## 7. 보안 및 제약사항

### 7.1 exec() 네임스페이스 격리

#### 7.1.1 메커니즘

CodeExecutor는 `exec(code, exec_globals)`를 사용하여 코드 실행:

```python
def execute(self, code: str):
    exec_globals = self._build_exec_globals()
    # exec_locals는 지정하지 않음 (globals와 같음)
    exec(code, exec_globals)
```

**exec_globals에 포함되는 것:**
- QGIS 공개 API: `qgis.core`, `PyQt5.QtCore` 등
- 기본 Python 모듈: `os`, `sys` 등
- `tools` (ToolRegistry 인스턴스)
- `ToolResult` 클래스

**exec_globals에 포함되지 않는 것:**
- 시스템 파일 시스템 전체 접근 불가 (os.path만 가능)
- 네트워크 소켓 직접 생성 불가
- 프로세스 생성 불가 (subprocess 제한)

#### 7.1.2 제약사항

| 작업 | 가능 여부 | 사유 |
|------|---------|------|
| QGIS API 호출 | ✓ | 공개 API만 노출 |
| tools.call() | ✓ | 명시적으로 주입 |
| 파일 읽기 (os.path) | ✓ | QGIS 프로젝트 경로 관련 |
| 네트워크 호출 | △ | requests 모듈 없음, urllib 가능 |
| 프로세스 생성 | ✗ | subprocess 제거됨 |
| 시스템 명령 실행 | ✗ | os.system 제거됨 |

### 7.2 도구 호출 검증

#### 7.2.1 파라미터 검증

ToolRegistry.call()에서 자동 수행:

```python
1. 도구 존재 확인
2. 필수 파라미터 확인
3. enum 제약 검증
4. 기본값 적용
5. Handler 호출
6. 예외 처리
```

#### 7.2.2 Handler 격리

각 도구의 handler는 어댑터에서 제공:
- DB 연결 정보 어댑터에 포함 (플러그인과 분리)
- 파라미터는 검증된 값만 전달
- 반환값은 ToolResult로 래핑

### 7.3 데이터베이스 연결 보안

#### 7.3.1 gis_layer_loader 연결

```python
# 어댑터에 하드코딩 (보안 고려)
DB_HOST = "geo-spatial-hub.postgres.database.azure.com"
DB_PORT = "6432"
DB_NAME = "dde-water"
DB_USER = "waterviewer"          # 읽기 전용 사용자 권장
DB_PASSWORD = "dohwaviewer"      # 환경변수 사용 권장 (향후)
```

**개선 방안:**
- 암호를 QGIS settings에 저장 (QSettings)
- 환경변수에서 로드
- QGIS credential manager 통합

#### 7.3.2 SQL Injection 방지

쿼리 구성 방식:

```python
# 안전한 방식 (준비된 명령)
query = f"SELECT * FROM public.{function_name}(%s)"
cursor.execute(query, (region_code,))

# 더 안전한 방식 (식별자 검증)
if function_name not in AVAILABLE_LAYERS_MAP:
    raise ValueError(f"Invalid function: {function_name}")
```

### 7.4 LLM 코드 실행 위험

#### 7.4.1 위험 시나리오

| 시나리오 | 위험도 | 완화 방안 |
|---------|--------|---------|
| LLM이 시스템 명령 생성 | 중간 | subprocess/os.system 제거 |
| LLM이 무한 루프 생성 | 낮음 | 사용자가 ctrl+C로 중단 |
| LLM이 대용량 메모리 할당 | 낮음 | QGIS 프로세스 메모리 제한 |
| LLM이 파일 삭제 | 낮음 | 프로젝트 디렉토리로 제한 |

#### 7.4.2 모니터링

```python
# CodeExecutor에서 타임아웃 구현 (향후)
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30초 제한
try:
    exec(code, exec_globals)
finally:
    signal.alarm(0)
```

### 7.5 권장사항

1. **프로덕션 배포 시:**
   - 데이터베이스 암호를 환경변수로 이동
   - QGIS credentials manager 통합
   - 코드 실행 타임아웃 구현
   - 로깅 추가 (도구 호출 기록)

2. **관리자 설정:**
   - 신뢰할 수 없는 LLM 제공자 사용 금지
   - 정기적인 감사

---

## 8. 구현 로드맵

### 8.1 작업 분해 (T1~T6)

```
T1: tool_schema.py 생성 (데이터 구조)
    ├─ ParameterDef
    ├─ ToolResult
    └─ ToolDefinition
            ↓
T2: tool_registry.py 생성 (중앙 레지스트리)
    ├─ register() / register_many()
    ├─ call() (파라미터 검증, 호출)
    ├─ generate_tools_prompt()
    ├─ scan_adapters()
    └─ scan_qgis_plugins()
            ↓
    ├──→ T3: code_executor.py 수정 (tools 주입)
    │
    ├──→ T4: prompt_manager.py + context_builder.py 수정
    │        (string.Template, 도구 요약)
    │
    ├──→ T5a: adapters/gis_layer_loader_adapter.py (4개 도구)
    │
    ├──→ T5b: adapters/base_plan_adapter.py (6개 도구)
    │
    └──→ T5c: plugin_main.py 수정 (ToolRegistry 초기화)
            ↓
            T6: 통합 테스트 및 검증
```

### 8.2 구현 순서 및 의존성

| 단계 | 작업 | 소요 시간 | 의존성 |
|------|------|---------|-------|
| 1 | T1: tool_schema.py | 1시간 | 없음 |
| 2 | T2: tool_registry.py | 2시간 | T1 |
| 3 | T3: code_executor.py 수정 | 30분 | T2 |
| 4 | T4: prompt_manager.py 수정 | 1시간 | T1, T2 |
| 5 | T5a: gis_layer_loader_adapter.py | 2시간 | T2 |
| 6 | T5b: base_plan_adapter.py | 1.5시간 | T2 |
| 7 | T5c: plugin_main.py 수정 | 1시간 | T2, T3, T4 |
| 8 | T6: 통합 테스트 | 3시간 | 모두 |
| **합계** | | **12시간** | |

### 8.3 커밋 전략

```
커밋 1: "feat(core): tool schema와 registry for MCP plugin tools"
  files: tool_schema.py, tool_registry.py

커밋 2: "feat(core): string.Template로 전환 및 도구 레지스트리 통합"
  files: code_executor.py, prompt_manager.py, context_builder.py

커밋 3: "feat(adapters): gis_layer_loader MCP tool adapter"
  files: adapters/__init__.py, adapters/gis_layer_loader_adapter.py

커밋 4: "feat(adapters): BasePlan MCP tool adapter"
  files: adapters/base_plan_adapter.py

커밋 5: "feat(plugin): ToolRegistry 초기화 및 플러그인 생명주기 연동"
  files: plugin_main.py

커밋 6: "test: 통합 테스트 및 검증"
  files: (테스트 자동화 또는 테스트 문서)
```

### 8.4 매일 마일스톤

```
Day 1 아침: T1, T2 완료 (기초 작업)
Day 1 오후: T3, T4 완료 (기존 코드 통합)
Day 2 아침: T5a, T5b 완료 (어댑터)
Day 2 오후: T5c 완료 (플러그인 연동)
Day 3 아침-오후: T6 (테스트, 버그 수정)
```

---

## 9. 테스트 시나리오

### 9.1 통합 테스트 8가지 시나리오

#### 시나리오 1: 도구 발견

**목표:** 플러그인이 로드되고 ToolRegistry에 등록되는지 확인

```python
# 테스트 코드
def test_tool_discovery():
    registry = ToolRegistry()

    # 어댑터 스캔
    count = registry.scan_adapters(iface)
    assert count > 0, "어댑터에서 도구 발견 안 됨"

    # 플러그인 스캔
    count += registry.scan_qgis_plugins(iface)
    assert count >= 10, "총 도구 10개 이상 필요"

    tools = registry.list_tools()
    assert "gis_layer_loader.load_db_layer" in tools
    assert "base_plan.load_target_area" in tools

# 성공 기준
- registry.list_tools()에 10개 이상의 도구 포함
- gis_layer_loader에서 4개, BasePlan에서 6개 도구 발견
```

#### 시나리오 2: 시스템 프롬프트 생성

**목표:** string.Template이 올바르게 작동하고 도구 정의가 포함되는지 확인

```python
def test_system_prompt_generation():
    prompt_manager = PromptManager()
    prompt_manager.set_context("레이어: [layer1, layer2]")

    registry = ToolRegistry()
    registry.scan_adapters(iface)
    tools_prompt = registry.generate_tools_prompt()

    prompt_manager.set_tools_prompt(tools_prompt)
    system_prompt = prompt_manager.get_system_prompt()

    # 검증
    assert "$context" not in system_prompt, "템플릿 변수 미대체"
    assert "$tools" not in system_prompt, "템플릿 변수 미대체"
    assert "{" in system_prompt, "Python 코드의 중괄호 보존"
    assert "processing.run" in system_prompt, "예시 코드 보존"
    assert "사용 가능한 플러그인 도구" in system_prompt, "도구 섹션 포함"
    assert "tools.call" in system_prompt, "도구 호출 예시 포함"

# 성공 기준
- string.Template 사용으로 ValueError 없음
- 시스템 프롬프트에 도구 정의 포함
- 기존 Python 코드 예시의 중괄호 모두 보존
```

#### 시나리오 3: 파라미터 검증

**목표:** ToolRegistry.call()이 파라미터를 올바르게 검증하는지 확인

```python
def test_parameter_validation():
    registry = ToolRegistry()
    registry.scan_adapters(iface)

    # 케이스 1: 필수 파라미터 누락
    result = registry.call("gis_layer_loader.load_db_layer", layer_name="건축물정보")
    assert not result.success
    assert "region_code" in result.error

    # 케이스 2: 허용되지 않는 enum 값
    result = registry.call("base_plan.set_drawing_extent", orientation="diagonal")
    assert not result.success
    assert "허용" in result.error

    # 케이스 3: 기본값 적용
    result = registry.call("base_plan.load_drawing_area")  # 파라미터 없음
    assert result.success or "로드" in str(result)

# 성공 기준
- 필수 파라미터 누락 시 명확한 오류
- enum 값 검증 작동
- 기본값 자동 적용
```

#### 시나리오 4: 도구 호출 성공

**목표:** DB 레이어 로드가 성공적으로 완료되는지 확인

```python
def test_tool_execution_success():
    registry = ToolRegistry()
    registry.scan_adapters(iface)

    # 도구 호출
    result = registry.call(
        "gis_layer_loader.load_db_layer",
        layer_name="건축물정보",
        region_code="11680"
    )

    # 검증
    assert result.success, f"도구 호출 실패: {result.error}"
    assert result.data is not None
    assert "layer_name" in result.data
    assert result.data["layer_name"] == "건축물정보"
    assert "feature_count" in result.data
    assert result.data["feature_count"] > 0

    # QGIS 프로젝트에 레이어 추가 확인
    layers = QgsProject.instance().mapLayers()
    assert any("건축물정보" in name for name in layers.values())

# 성공 기준
- ToolResult.success = True
- 레이어가 QGIS 프로젝트에 추가됨
- feature_count > 0
```

#### 시나리오 5: 자동 출력 (print)

**목표:** ToolResult가 자동으로 print되어 stdout에 나타나는지 확인

```python
def test_tool_result_auto_print(capsys):
    registry = ToolRegistry()
    registry.scan_adapters(iface)

    result = registry.call(
        "gis_layer_loader.load_db_layer",
        layer_name="건축물정보",
        region_code="11680"
    )

    # stdout 캡처
    captured = capsys.readouterr()

    # 검증
    assert "[성공]" in captured.out
    assert "건축물정보" in captured.out

# 성공 기준
- tools.call() 호출 시 자동으로 결과 print
- "[성공]" 또는 "[실패]" 프리픽스 포함
- 채팅 패널에서 볼 수 있는 형식
```

#### 시나리오 6: 기존 기능 호환성

**목표:** 도구 없이도 기존 code-gen/execute가 작동하는지 확인

```python
def test_backward_compatibility():
    # 도구 없이 CodeExecutor 초기화
    executor = CodeExecutor(iface, tool_registry=None)

    code = """
layer = QgsProject.instance().mapLayersByName("layer1")[0]
print(f"레이어: {layer.name()}")
"""

    # 실행 성공
    executor.execute(code)

    # tools 변수 접근 불가
    code_with_tools = "result = tools.call('tool')"
    try:
        executor.execute(code_with_tools)
        # 실패 예상
    except NameError:
        # 정상 (tools 없음)
        pass

# 성공 기준
- ToolRegistry 없어도 기존 코드 정상 작동
- 기존 코드 생성 결과 동일
```

#### 시나리오 7: 서드파티 플러그인 등록

**목표:** 플러그인이 mcp_tools() 규칙으로 등록하는지 확인

```python
class MockPlugin:
    def mcp_tools(self, iface):
        return [
            ToolDefinition(
                name="mock_plugin.test_tool",
                description="테스트 도구",
                parameters={},
                handler=lambda: ToolResult(success=True, data="success"),
                plugin_name="mock_plugin"
            )
        ]

def test_third_party_registration():
    registry = ToolRegistry()

    # 플러그인 스캔 시뮬레이션
    mock_plugin = MockPlugin()
    tools = mock_plugin.mcp_tools(iface)
    registry.register_many(tools)

    # 호출
    result = registry.call("mock_plugin.test_tool")
    assert result.success
    assert result.data == "success"

# 성공 기준
- 플러그인의 mcp_tools() 메서드 자동 발견
- 도구 자동 등록
```

#### 시나리오 8: 다단계 BasePlan 워크플로우

**목표:** 다단계 도구 호출로 완전한 도면 생성 프로세스를 확인

```python
def test_base_plan_workflow():
    registry = ToolRegistry()
    registry.scan_adapters(iface)

    # 단계 1: 대상 영역 로드
    result1 = registry.call("base_plan.load_target_area", admin_code="11680")
    assert result1.success, f"Area A 로드 실패: {result1.error}"

    # 단계 2: 도면 범위 설정
    result2 = registry.call("base_plan.set_drawing_extent", orientation="horizontal")
    assert result2.success, f"도면 범위 설정 실패: {result2.error}"

    # 단계 3: 도면 영역 로드
    result3 = registry.call("base_plan.load_drawing_area")
    assert result3.success, f"Area B 로드 실패: {result3.error}"

    # 단계 4: 오버레이 추가
    for overlay in ["north_arrow", "scale_bar", "outer_gradient"]:
        result = registry.call("base_plan.add_overlay", overlay_type=overlay)
        assert result.success, f"{overlay} 추가 실패"

    # 단계 5: 내보내기
    result5 = registry.call("base_plan.export", format="pdf")
    assert result5.success, f"PDF 내보내기 실패"
    assert "file_path" in result5.data

# 성공 기준
- 5단계 모두 성공
- 최종 PDF 파일 생성 확인
```

### 9.2 성공 기준 요약

| 시나리오 | 성공 기준 | 검증 방법 |
|---------|---------|---------|
| 도구 발견 | 10+ 도구 등록 | registry.list_tools() |
| 프롬프트 생성 | 중괄호 보존, 도구 섹션 포함 | 문자열 검사 |
| 파라미터 검증 | 오류 감지 정확 | ToolResult.success 확인 |
| 도구 호출 성공 | QGIS 프로젝트에 레이어 추가 | QgsProject 검사 |
| 자동 출력 | "[성공]" 출력 | stdout 캡처 |
| 호환성 | 기존 코드 작동 | CodeExecutor 테스트 |
| 서드파티 | mcp_tools() 인식 | 플러그인 스캔 |
| 복합 워크플로우 | PDF 생성 완료 | 파일 존재 확인 |

---

## 10. 용어집

### 핵심 용어

| 용어 | 약자 | 정의 |
|------|------|------|
| **MCP** | Model Context Protocol | LLM이 외부 도구/API를 호출하는 프로토콜 (Anthropic 표준) |
| **ToolDefinition** | - | 도구의 메타데이터 (이름, 설명, 파라미터, 핸들러) |
| **ToolResult** | - | 도구 호출 결과 (success, data, error) |
| **ToolRegistry** | - | 도구를 등록하고 관리하는 중앙 싱글톤 |
| **Handler** | - | ToolDefinition에서 실제 기능을 수행하는 Python 함수/메서드 |
| **Adapter** | - | 플러그인의 기능을 ToolDefinition으로 래핑하는 모듈 |
| **Parameter Validation** | - | 도구 호출 시 파라미터 필수/optional, enum 검증 |
| **Enum Constraint** | - | 파라미터가 특정 값들만 허용하는 제약 |
| **System Prompt** | - | LLM에 전달되는 시스템 지시사항 (도구 정의 포함) |
| **string.Template** | - | Python 표준 라이브러리의 템플릿 클래스 ($var 기반) |
| **Singleton** | - | 전체 프로세스에서 단 하나만 존재하는 인스턴스 |
| **In-Process** | - | 외부 프로세스 없이 QGIS Python 환경 내에서 작동 |

### QGIS 관련 용어

| 용어 | 정의 |
|------|------|
| **QgisInterface (iface)** | QGIS의 핵심 인터페이스 객체 |
| **QgsProject** | 현재 QGIS 프로젝트 |
| **QgsVectorLayer** | 벡터 레이어 (점/선/면) |
| **QgsRasterLayer** | 래스터 레이어 (이미지, DEM 등) |
| **QgsDataSourceUri** | 데이터 소스 연결 정보 |
| **PyQGIS** | QGIS Python API |

### 프로젝트 관련 용어

| 용어 | 정의 |
|------|------|
| **gis_layer_loader** | 계층적 행정구역 선택으로 DB 레이어 로드 플러그인 |
| **BasePlan_opt** | 토목 기본도면 생성 플러그인 |
| **Area A (대상 영역)** | 지도에서 선택된 행정구역 영역 |
| **Area B (도면 영역)** | A0 용지 크기로 설정된 도면 범위 |
| **Admin Code (행정 코드)** | 한국 행정구역 표준 코드 (2~8자리) |
| **WMS** | Web Map Service (GeoServer 기반 지도 서비스) |

---

## 마치며

이 설계문서는 QGIS-autocoder MCP 플러그인 도구 레지스트리의 완전한 기술 설명서입니다. 구현 시 이 문서를 참고하여 일관된 아키텍처를 유지하고, 테스트 시나리오를 검증하여 품질을 보장하시기 바랍니다.

**주요 성공 포인트:**
1. string.Template으로 템플릿 문제 해결
2. 싱글톤 ToolRegistry로 중앙 관리
3. 어댑터 패턴으로 플러그인 독립성 확보
4. 자동 print로 결과 가시성 보장
5. 완벽한 역호환성 유지

