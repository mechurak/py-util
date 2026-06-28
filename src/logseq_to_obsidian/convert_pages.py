"""Logseq pages를 Obsidian 친화적 마크다운으로 변환.

Logseq는 모든 줄이 불릿인 아웃라이너 구조라, Obsidian으로 가져오면
헤딩 앞에도 `- `가 붙고 하위 내용이 불필요하게 한 단계 들여써진다.
코드블럭도 `- ``` ` 형태에 내부가 공백으로 들여써져 있다.

이 스크립트는 다음을 정리한다:

  - `- ## 제목` -> `## 제목`            (헤딩을 col 0으로 승격, 들여쓰기 기준 리셋)
  - 헤딩 하위 불릿의 들여쓰기를 한 단계 제거 (상대적 중첩은 보존)
  - `- ``` ` 코드블럭 -> 독립 코드블럭으로, 내부 공통 들여쓰기 제거
  - :LOGBOOK: ~ :END: 드로어 제거, TODO/DONE -> 체크박스 (clean_logseq_body 재사용)

변환 전:                         변환 후:
  - ## Root 보안                  ## Root 보안
  \t- MFA 활성화                  - MFA 활성화
  \t\t- 우측 상단 ...             \t- 우측 상단 ...
  - ```                          ```
  \x20\x20\x20\x20\x20\x20aws iam ...     aws iam ...
  \x20\x20\x20\x20\x20\x20```            ```

사용법:
  uv run python src/logseq_to_obsidian/convert_pages.py [--dry-run]
"""

import argparse
import re
import sys
from pathlib import Path

from convert_journal import clean_logseq_body, get_env_dir


def _leading_tabs(s: str) -> int:
    return len(re.match(r"^\t*", s).group(0))


def flatten_outline(text: str) -> str:
    """Logseq 아웃라인을 일반 마크다운으로 평탄화한다.

    헤딩을 만나면 들여쓰기 기준(base)을 그 헤딩 깊이+1로 리셋하고,
    이후 불릿들은 base만큼 들여쓰기를 줄여 헤딩의 직속 자식이
    최상위 불릿이 되도록 한다. 코드블럭은 독립 블록으로 빼낸다.
    """
    lines = text.split("\n")
    out: list[str] = []
    base = 0
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        indent = _leading_tabs(line)
        rest = line[indent:]

        # 선두 불릿 마커 분리
        bullet = False
        content = rest
        if rest.startswith("- "):
            bullet, content = True, rest[2:]
        elif rest == "-":
            bullet, content = True, ""

        sc = content.lstrip()

        # --- 코드블럭 ---
        if sc.startswith("```"):
            fence_open = sc  # 언어 힌트 보존 (```python 등)
            code: list[str] = []
            i += 1
            while i < n:
                if lines[i].lstrip().startswith("```"):
                    i += 1
                    break
                code.append(lines[i])
                i += 1
            nonempty = [l for l in code if l.strip()]
            common = min((len(l) - len(l.lstrip(" \t")) for l in nonempty), default=0)
            dedented = [l[common:] if l.strip() else "" for l in code]
            if out and out[-1] != "":
                out.append("")
            out.append(fence_open)
            out.extend(dedented)
            out.append("```")
            out.append("")
            continue

        # --- 헤딩 ---
        if re.match(r"#{1,6}\s", sc):
            if out and out[-1] != "":
                out.append("")
            out.append(sc)
            out.append("")
            base = indent + 1
            i += 1
            continue

        # --- 빈 불릿(`- `): Logseq의 한 줄 띄우기용 -> 빈 줄 ---
        if bullet and not content.strip():
            out.append("")
            i += 1
            continue

        # --- 일반 줄 ---
        prefix = "\t" * max(indent - base, 0)
        out.append(prefix + ("- " + content if bullet else content))
        i += 1

    # 연속 빈 줄 1개로 축약
    result: list[str] = []
    for l in out:
        if l == "" and result and result[-1] == "":
            continue
        result.append(l)
    return "\n".join(result).rstrip("\n") + "\n"


def convert_page(text: str) -> str:
    """Logseq 문법 정리 후 아웃라인 평탄화까지 적용한다."""
    return flatten_outline(clean_logseq_body(text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Logseq pages를 Obsidian 마크다운으로 변환")
    parser.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 생성/스킵 목록만 출력")
    parser.add_argument("--overwrite", action="store_true", help="대상 파일이 이미 있어도 덮어쓰기")
    args = parser.parse_args()

    src = get_env_dir("LOGSEQ_PAGES_DIR")
    dst = get_env_dir("OBSIDIAN_PAGES_DIR")

    files = sorted(src.glob("*.md"))
    if not files:
        sys.exit(f"변환할 page 파일이 없습니다: {src}")

    created = skipped = 0
    for f in files:
        out_path = dst / f.name
        if out_path.exists() and not args.overwrite:
            print(f"skip   {out_path.relative_to(dst)}  (이미 존재, --overwrite 로 덮어쓰기)")
            skipped += 1
            continue

        content = convert_page(f.read_text(encoding="utf-8").rstrip("\n"))
        if args.dry_run:
            print(f"create {out_path.relative_to(dst)}")
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            print(f"create {out_path.relative_to(dst)}")
        created += 1

    label = "(dry-run) " if args.dry_run else ""
    print(f"\n{label}완료: 생성 {created}개 / skip {skipped}개")


if __name__ == "__main__":
    main()
