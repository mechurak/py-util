"""교보문고 도서 페이지에서 목차를 추출하여 Logseq 페이지 형식으로 변환한다.

교보문고는 봇 요청을 차단하므로 Playwright(headless Chrome)를 사용하여 페이지를 렌더링한다.

실행 방법:
    # 교보문고 URL로 목차 추출 (stdout 출력)
    uv run python src/toc_extractor/kyobo.py https://product.kyobobook.co.kr/detail/S000218753254

    # 결과를 파일로 저장
    uv run python src/toc_extractor/kyobo.py https://product.kyobobook.co.kr/detail/S000218753254 -o output.md

사전 준비:
    uv run playwright install chromium
"""

import re
import sys
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

KYOBOBOOK_URL_PATTERN = re.compile(r"https://product\.kyobobook\.co\.kr/detail/\w+")

# 목차 라인 패턴
PART_PATTERN = re.compile(r"^\[(?:PART\s*)?(\d+부?)\]\s*(.+)", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^(?:Chapter\s+)?(\d+)\s*[_.\s]\s*(.+)", re.IGNORECASE)
APPENDIX_PATTERN = re.compile(r"^(Appendix\s*\w+)[._]?\s*(.+)", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(\d+\.\d+)\s+(.+)")
SUBSECTION_PATTERN = re.compile(r"^(\d+\.\d+\.\d+)\s+(.+)")


@dataclass
class BookInfo:
    title: str = ""
    author: str = ""
    publisher: str = ""
    release_date: str = ""
    cover_image: str = ""
    url: str = ""
    toc_lines: list[str] = field(default_factory=list)


def fetch_page(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(".product_detail_area.book_contents", timeout=15000)
        html = page.content()
        browser.close()
    return html


def parse_book_info(html: str, url: str) -> BookInfo:
    soup = BeautifulSoup(html, "html.parser")
    info = BookInfo(url=url)

    # 제목
    h1 = soup.select_one("h1")
    if h1:
        info.title = re.sub(r"\s+", " ", h1.get_text(strip=True))

    # 표지 이미지
    og_image = soup.select_one("meta[property='og:image']")
    if og_image:
        info.cover_image = og_image.get("content", "")

    body_text = soup.get_text()

    # 저자 — 페이지 타이틀에서 추출: "책 제목 | 저자 - 교보문고"
    title_tag = soup.select_one("title")
    if title_tag:
        m = re.search(r"\|\s*(.+?)\s*-\s*교보문고", title_tag.get_text())
        if m:
            info.author = m.group(1)

    # 출판사
    publisher_el = soup.select_one("a[href*='pbcmCode']")
    if publisher_el:
        info.publisher = publisher_el.get_text(strip=True)

    # 출간일
    date_match = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", body_text)
    if date_match:
        info.release_date = f"{date_match.group(1)}-{date_match.group(2)}"

    # 목차
    toc_el = soup.select_one(".product_detail_area.book_contents")
    if toc_el:
        toc_item = toc_el.select_one(".book_contents_item")
        if toc_item:
            for br in toc_item.find_all("br"):
                br.replace_with("\n")
            raw_text = toc_item.get_text()
            info.toc_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    return info


def classify_line(line: str) -> tuple[str, str, str]:
    """목차 라인을 분류한다. (type, number, title) 반환."""
    # __ 접두어 제거 (교보문고에서 하위 항목에 붙임)
    stripped = re.sub(r"^_+\s*", "", line)

    if m := PART_PATTERN.match(stripped):
        part_num = m.group(1)
        # "1" -> "1부", "1부" -> "1부"
        if not part_num.endswith("부"):
            part_num += "부"
        return "part", part_num, m.group(2).strip()
    if m := APPENDIX_PATTERN.match(stripped):
        return "appendix", m.group(1), m.group(2).strip()
    if m := SUBSECTION_PATTERN.match(stripped):
        return "subsection", m.group(1), m.group(2).strip()
    if m := SECTION_PATTERN.match(stripped):
        return "section", m.group(1), m.group(2).strip()
    if m := CHAPTER_PATTERN.match(stripped):
        num = m.group(1)
        title = re.sub(r"^[_.\s]+", "", m.group(2)).strip()
        return "chapter", num, title

    return "other", "", stripped


def toc_to_logseq(info: BookInfo) -> str:
    """BookInfo를 Logseq 페이지 마크다운 형식으로 변환한다."""
    lines = []

    # 프로퍼티 블록
    lines.append("- type:: book")
    if info.cover_image:
        lines.append(f"  cover:: ![표지]({info.cover_image}){{:width 150}}")
    if info.release_date:
        lines.append(f"  release:: {info.release_date}")
    lines.append("  tags:: ")

    # 링크
    lines.append(f"- 교보문고 링크 : {info.url}")

    # 목차 변환
    for raw_line in info.toc_lines:
        line_type, number, title = classify_line(raw_line)

        if line_type == "part":
            lines.append(f"- ## [{number}] {title}")
        elif line_type == "chapter":
            lines.append(f"- ## Chapter {number}. {title}")
        elif line_type == "appendix":
            lines.append(f"- ## {number}. {title}")
        elif line_type == "section":
            lines.append(f"  - {number} {title}")
        elif line_type == "subsection":
            lines.append(f"    - {number} {title}")
        elif line_type == "other":
            if title:
                lines.append(f"  - {title}")

    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python src/toc_extractor/kyobo.py <교보문고_URL> [-o output.md]")
        sys.exit(1)

    url = sys.argv[1]
    if not KYOBOBOOK_URL_PATTERN.match(url):
        print(f"Error: 유효한 교보문고 상품 URL이 아닙니다: {url}")
        sys.exit(1)

    output_path = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    html = fetch_page(url)
    info = parse_book_info(html, url)

    if not info.toc_lines:
        print("Error: 목차를 찾을 수 없습니다.")
        sys.exit(1)

    result = toc_to_logseq(info)

    if output_path:
        from pathlib import Path

        Path(output_path).write_text(result, encoding="utf-8")
        print(f"저장 완료: {output_path}")
        print(f"  제목: {info.title}")
        print(f"  저자: {info.author}")
        print(f"  출판사: {info.publisher}")
        print(f"  출간일: {info.release_date}")
        print(f"  목차 항목: {len(info.toc_lines)}개")
    else:
        print(result)


if __name__ == "__main__":
    main()
