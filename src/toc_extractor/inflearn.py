# 강의 제목 눌러 들어간 페이지에서 대시보드 밑쪽에 강의 커리큘럼 모두 펼치기
# 개발자모드(F12)에서 강의 목록들 다 포함되도록 복사해서 inflearn.html 로 같은 폴더에 저장 후 요 스크립트 실행


import re
from pathlib import Path

from bs4 import BeautifulSoup

# 스크립트와 같은 폴더에 저장한 inflearn.html 파일을 읽어들임
source = open(Path(__file__).parent / "inflearn.html", encoding="UTF-8")
soup = BeautifulSoup(source, "html.parser")
sections = soup.select(".mantine-Accordion-item")  # 섹션 + 동영상들 포함


for section in sections:
    # 섹션 제목 추출 (예: '교육 환경 준비')
    section_title = re.sub(r"\s+", " ", section.select_one(".css-542wex").get_text()).strip()
    print(f"- ## 📚 {section_title}")

    # 섹션 안의 개별 동영상(클립) 목록
    clips = section.select(".css-rf14v6")
    for clip in clips:
        # HTML 들여쓰기로 생긴 연속 공백/개행을 단일 공백으로 치환
        title = re.sub(r"\s+", " ", clip.get_text()).strip()
        print(f"- ## {title}")
