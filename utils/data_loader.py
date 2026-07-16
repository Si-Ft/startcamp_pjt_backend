import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_FILES = {
    "관광지": "대전_충청권_관광지.json",
    "음식점": "대전_충청권_음식점.json",
    "숙박": "대전_충청권_숙박.json",
    "축제": "대전_충청권_축제공연행사.json",
    "문화시설": "대전_충청권_문화시설.json",
    "쇼핑": "대전_충청권_쇼핑.json",
    "레포츠": "대전_충청권_레포츠.json",
    "여행코스": "대전_충청권_여행코스.json",
}


def detect_category(question: str):

    q = question.lower()

    if any(word in q for word in ["맛집", "음식", "식당", "먹거리"]):
        return "음식점"

    if any(word in q for word in ["숙박", "호텔", "펜션"]):
        return "숙박"

    if any(word in q for word in ["축제", "행사"]):
        return "축제"

    if any(word in q for word in ["쇼핑", "마트", "쇼핑몰", "백화점"]):
        return "쇼핑"

    if any(word in q for word in ["박물관", "미술관", "문화"]):
        return "문화시설"

    if any(word in q for word in ["레포츠", "체험"]):
        return "레포츠"

    if any(word in q for word in ["코스", "여행코스"]):
        return "여행코스"

    return "관광지"


def load_data(category):

    filename = DATA_FILES.get(category)

    if filename is None:
        return []

    path = os.path.join(BASE_DIR, "data", filename)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data["items"]


def search_items(question, items, limit=15):

    keywords = [
        word.strip()
        for word in question.split()
        if len(word.strip()) >= 2
    ]

    results = []

    for item in items:

        text = (
            f'{item.get("title","")} '
            f'{item.get("addr1","")} '
            f'{item.get("addr2","")}'
        )

        score = 0

        for keyword in keywords:
            if keyword in text:
                score += 1

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    if results:
        return [item for _, item in results[:limit]]

    return items[:limit]


def build_context(items):

    context = ""

    for index, item in enumerate(items, start=1):

        context += f"""
[{index}]
장소명: {item.get("title","")}
주소: {item.get("addr1","")}
분류: {item.get("contenttypeid","")}
"""

    return context