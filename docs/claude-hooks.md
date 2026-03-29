# Claude Code Hooks 설명

## ruff format hook (PostToolUse)

[`.claude/settings.json`](../.claude/settings.json)에 설정된 hook으로, Claude가 Write/Edit 도구로 파일을 수정한 후 자동으로 ruff format을 실행합니다.

### command 분석

```bash
jq -r '.tool_response.filePath // .tool_input.file_path' \
  | { read -r f; case "$f" in *.py) uv run ruff format "$f" ;; esac; } \
  2>/dev/null || true
```

**1. 파일 경로 추출**

```bash
jq -r '.tool_response.filePath // .tool_input.file_path'
```

- stdin으로 받은 JSON에서 파일 경로를 추출
- Write는 `tool_response.filePath`, Edit는 `tool_input.file_path`에 경로가 있으므로 `//` (alternative operator)로 둘 다 커버

**2. 변수 저장**

```bash
read -r f
```

- 파이프로 받은 파일 경로를 변수 `f`에 저장

**3. .py 파일 필터링**

```bash
case "$f" in
  *.py)
    uv run ruff format "$f"
    ;;
esac
```

- `.py` 파일인 경우에만 ruff format 실행
- 그 외 파일은 무시
- `*.py)` 처럼 닫는 괄호만 쓰는 것이 bash `case` 문의 일반적인 관용. `(*.py)` 처럼 여는 괄호를 붙일 수도 있지만 거의 쓰지 않음

**4. ruff 실행**

```bash
uv run ruff format "$f"
```

- ruff가 PATH에 없으므로 `uv run`으로 실행
- 따옴표로 경로의 공백도 안전하게 처리

**5. 에러 방어**

```bash
2>/dev/null || true
```

- stderr 숨기고, 에러 시에도 exit 0 반환
- hook 실패가 Claude 작업을 중단시키지 않도록 방어
