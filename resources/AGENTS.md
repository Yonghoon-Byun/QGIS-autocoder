<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-25 | Updated: 2026-02-25 -->

# resources/

## Purpose
플러그인 아이콘 등 정적 리소스 파일을 보관하는 디렉터리. QGIS 툴바 및 메뉴에 표시되는 아이콘을 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `icon.svg` | 플러그인 툴바/메뉴 아이콘 (SVG 형식) |

## For AI Agents

### Working In This Directory
- `plugin_main.py`의 `initGui()`에서 `icon.svg` → `icon.png` 순서로 아이콘 탐색
- SVG 파일이 없으면 PNG 파일을 시도하고, 둘 다 없으면 빈 아이콘 사용
- `metadata.txt`에는 `icon=resources/icon.png`로 명시되어 있으나 실제로는 SVG 우선

### Common Patterns
```python
# plugin_main.py의 아이콘 로드 패턴
icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.svg')
if not os.path.exists(icon_path):
    icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.png')
```

## Dependencies

### Internal
- `plugin_main.py` — 아이콘 경로 참조

<!-- MANUAL: -->
