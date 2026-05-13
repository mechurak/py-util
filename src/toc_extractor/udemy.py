# 강의 섹션 다 펼친 후, 개발자모드(F12)에서 강의 목록들 다 포함되도록 복사해서 udemy.html 로 같은 폴더에 저장 후 요 스크립트 실행


import re
from pathlib import Path

from bs4 import BeautifulSoup

# 스크립트와 같은 폴더에 저장한 udemy.html 파일을 읽어들임
source = open(Path(__file__).parent / "udemy.html", encoding="UTF-8")
soup = BeautifulSoup(source, "html.parser")
sections = soup.select('[data-purpose^="section-panel"]')  # 섹션 하나 다 감싸는 패널


for section in sections:
    # 섹션 제목 추출 (예: 'Section 1: Introduction')
    title_el = section.select_one(".ud-accordion-panel-title")
    section_title = re.sub(r"\s+", " ", title_el.get_text()).strip()
    print(f"- ## 📚 {section_title}")

    # 섹션 안의 개별 강의(아이템) 목록
    items = section.select('[data-purpose="item-title"]')
    for item in items:
        title = re.sub(r"\s+", " ", item.get_text()).strip()
        print(f"  - {title}")
