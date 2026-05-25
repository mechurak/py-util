# intigo 모드에서 강의 사이트 들어가면 overview 에서 강의 섹션 다 펼칠 수 있음
# 개발자모드(F12)에서 강의 목록들 다 포함되도록 복사해서 udemy.html 로 같은 폴더에 저장 후 요 스크립트 실행


import re
from pathlib import Path

from bs4 import BeautifulSoup

# 스크립트와 같은 폴더에 저장한 udemy.html 파일을 읽어들임
source = open(Path(__file__).parent / "udemy.html", encoding="UTF-8")
soup = BeautifulSoup(source, "html.parser")
sections = soup.select('[class*="section--panel--"]')  # 섹션 하나 다 감싸는 패널

if not sections:
    raise SystemExit("섹션을 하나도 찾지 못했습니다. udemy.html 구조가 바뀌었을 수 있으니 셀렉터를 확인하세요.")

for section in sections:
    # 섹션 제목 추출 (예: 'Introduction')
    title_el = section.select_one('[class*="section--section-title--"]')
    section_title = re.sub(r"\s+", " ", title_el.get_text()).strip()
    print(f"- ## 📚 {section_title}")

    # 섹션 안의 개별 강의(아이템) 목록
    items = section.select('[data-testid="course-lecture-title"]')
    for item in items:
        title = re.sub(r"\s+", " ", item.get_text()).strip()
        print(f"  - {title}")
