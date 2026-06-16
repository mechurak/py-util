"""Logseq journals를 Obsidian 주간 journal 문서로 변환.

Logseq는 하루 1파일(YYYY_MM_DD.md)로 정리되어 있고,
Obsidian은 연도 폴더 아래 일주일(일~토) 단위 문서로 정리한다.

  Logseq:   journals/2025_01_06.md
  Obsidian: Journals/2025/20250105-W02.md   # 그 주 일요일(2025-01-05) 기준

문서 내부는 날짜별 헤딩으로 구분한다:

  ## 2025-01-05 (Sun)
  - temp
  - temp

  ## 2025-01-06 (Mon)
  - ...원본 불릿...

사용법:
  uv run python src/logseq_to_obsidian/convert_journal.py [--dry-run]
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# 기록이 없는 날에 채울 플레이스홀더
EMPTY_DAY_BODY = "- temp\n- temp"

# Logseq 작업 마커 -> Obsidian 체크박스
DONE_MARKERS = {"DONE"}
TODO_MARKERS = {"TODO", "DOING", "NOW", "LATER", "WAITING"}
_TASK_RE = re.compile(r"^(\s*)-\s+(TODO|DOING|NOW|LATER|WAITING|DONE)\s+(.*)$")


def clean_logseq_body(text: str) -> str:
    """Logseq 전용 문법을 Obsidian 친화적으로 정리한다.

    - :LOGBOOK: ~ :END: 드로어(시간 추적) 제거
    - DONE -> [x], TODO/DOING/NOW/LATER/WAITING -> [ ] 체크박스로 변환
    """
    out: list[str] = []
    in_logbook = False
    for line in text.split("\n"):
        stripped = line.strip()
        if in_logbook:
            if stripped == ":END:":
                in_logbook = False
            continue
        if stripped == ":LOGBOOK:":
            in_logbook = True
            continue

        m = _TASK_RE.match(line)
        if m:
            indent, marker, rest = m.groups()
            box = "[x]" if marker in DONE_MARKERS else "[ ]"
            out.append(f"{indent}- {box} {rest}")
        else:
            out.append(line)
    return "\n".join(out)


def get_env_dir(name: str) -> Path:
    """필수 환경변수에서 디렉터리 경로를 읽는다. 없으면 종료."""
    value = os.getenv(name)
    if not value:
        sys.exit(f"오류: 환경변수 {name} 가 설정되지 않았습니다. .env 파일을 확인하세요.")
    path = Path(value)
    if not path.is_dir():
        sys.exit(f"오류: {name} 경로가 존재하지 않습니다: {path}")
    return path


def parse_journal_files(src: Path) -> dict[date, str]:
    """YYYY_MM_DD.md 파일들을 {날짜: 본문} 매핑으로 읽는다."""
    days: dict[date, str] = {}
    for f in sorted(src.glob("*.md")):
        try:
            d = date(*(int(p) for p in f.stem.split("_")))
        except (ValueError, TypeError):
            print(f"건너뜀(파일명 형식 불일치): {f.name}")
            continue
        days[d] = clean_logseq_body(f.read_text(encoding="utf-8").rstrip("\n"))
    return days


def week_sunday(d: date) -> date:
    """해당 날짜가 속한 주(일~토)의 일요일을 반환한다."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def week_filename(sunday: date) -> str:
    """주간 문서 파일명: 20250105-W02.md (일요일 날짜 + %U 기준 주차)."""
    week_num = int(sunday.strftime("%U")) + 1
    return f"{sunday:%Y%m%d}-W{week_num:02d}.md"


def build_week_content(sunday: date, days: dict[date, str]) -> str:
    """일요일부터 토요일까지 7일의 날짜별 헤딩 문서를 만든다."""
    blocks = []
    for i in range(7):
        d = sunday + timedelta(days=i)
        heading = f"## {d:%Y-%m-%d} ({d:%a})"
        body = days.get(d, EMPTY_DAY_BODY)
        blocks.append(f"{heading}\n{body}")
    return "\n\n".join(blocks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Logseq journals를 Obsidian 주간 문서로 변환")
    parser.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 생성/스킵 목록만 출력")
    args = parser.parse_args()

    src = get_env_dir("LOGSEQ_JOURNALS_DIR")
    dst = get_env_dir("OBSIDIAN_JOURNALS_DIR")

    days = parse_journal_files(src)
    if not days:
        sys.exit(f"변환할 journal 파일이 없습니다: {src}")

    # 일요일 기준으로 주별 그룹핑
    weeks: dict[date, list[date]] = defaultdict(list)
    for d in days:
        weeks[week_sunday(d)].append(d)

    created = skipped = 0
    for sunday in sorted(weeks):
        # 폴더/파일명은 주 시작(일요일)의 연도 기준
        out_path = dst / str(sunday.year) / week_filename(sunday)

        if out_path.exists():
            print(f"skip   {out_path.relative_to(dst)}  (이미 존재)")
            skipped += 1
            continue

        content = build_week_content(sunday, days)
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
