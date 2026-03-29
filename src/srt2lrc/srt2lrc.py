"""SRT to LRC 변환기.

TurboScribe로 생성한 SRT 자막 파일을 안드로이드 플레이어 앱용 LRC 가사 파일로 변환한다.
TurboScribe 워터마크는 자동으로 제거된다.

실행 방법:
    # srt2lrc 폴더 내 모든 .srt 파일을 일괄 변환
    uv run python src/srt2lrc/srt2lrc.py

    # 특정 파일만 변환
    uv run python src/srt2lrc/srt2lrc.py src/srt2lrc/englishbook_new_01-1.srt

    # 여러 파일 지정
    uv run python src/srt2lrc/srt2lrc.py file1.srt file2.srt file3.srt

변환 결과는 같은 폴더에 .lrc 확장자로 생성된다.
"""

import re
import sys
from pathlib import Path

TURBOSCRIBE_PATTERN = re.compile(r"\(TurboScribe.*?\)\s*")
SRT_TIMESTAMP = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def srt_time_to_lrc(timestamp: str) -> str:
    """Convert SRT timestamp (HH:MM:SS,mmm) to LRC timestamp ([MM:SS.xx])."""
    m = SRT_TIMESTAMP.match(timestamp)
    if not m:
        raise ValueError(f"Invalid SRT timestamp: {timestamp}")
    hours, minutes, seconds, millis = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    total_minutes = hours * 60 + minutes
    centiseconds = millis // 10
    return f"[{total_minutes:02d}:{seconds:02d}.{centiseconds:02d}]"


def convert_srt_to_lrc(srt_text: str) -> str:
    """Convert SRT content to LRC format."""
    lines = []
    blocks = re.split(r"\n\n+", srt_text.strip())

    for block in blocks:
        block_lines = block.strip().split("\n")
        if len(block_lines) < 2:
            continue

        # Find timestamp line
        timestamp_line = None
        text_start = 0
        for i, line in enumerate(block_lines):
            if "-->" in line:
                timestamp_line = line
                text_start = i + 1
                break

        if not timestamp_line:
            continue

        start_time = timestamp_line.split("-->")[0].strip()
        lrc_time = srt_time_to_lrc(start_time)

        # Join multi-line subtitle text
        text = " ".join(block_lines[text_start:]).strip()

        # Remove TurboScribe watermark
        text = TURBOSCRIBE_PATTERN.sub("", text).strip()

        if text:
            lines.append(f"{lrc_time}{text}")

    return "\n".join(lines) + "\n"


def convert_file(srt_path: Path) -> Path:
    """Convert a single SRT file to LRC. Returns the output path."""
    srt_text = srt_path.read_text(encoding="utf-8")
    lrc_text = convert_srt_to_lrc(srt_text)
    lrc_path = srt_path.with_suffix(".lrc")
    lrc_path.write_text(lrc_text, encoding="utf-8")
    return lrc_path


def main():
    srt_dir = Path(__file__).parent

    if len(sys.argv) > 1:
        srt_files = [Path(p) for p in sys.argv[1:]]
    else:
        srt_files = sorted(srt_dir.glob("*.srt"))

    if not srt_files:
        print("No SRT files found.")
        return

    for srt_file in srt_files:
        lrc_path = convert_file(srt_file)
        print(f"Converted: {srt_file.name} -> {lrc_path.name}")


if __name__ == "__main__":
    main()
