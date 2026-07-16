import os
import time
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_chatbot_db
from models import ChatSession, ChatMessage
from utils.data_loader import (
    detect_category,
    load_data,
    search_items,
    build_context,
)
import re

# 프롬프트에 실어 보낼 최근 대화 턴 수 (그 이전 대화는 summary로 압축)
HISTORY_TURN_LIMIT = 5


def format_answer(text: str) -> str:
    """
    GPT 관광 답변 출력 포맷 정리
    """

    # 장소 번호 앞 줄바꿈
    text = re.sub(
        r"\s*(①|②|③|④|⑤)",
        r"\n\n\1",
        text
    )


    # 설명 앞 줄바꿈
    text = re.sub(
        r"\s*설명:",
        "\n\n설명:",
        text
    )


    # 위치 앞 줄바꿈
    text = re.sub(
        r"\s*위치:",
        "\n위치:",
        text
    )


    # 추가 팁
    text = re.sub(
        r"\s*💡",
        "\n\n💡",
        text
    )


    # 질문
    text = re.sub(
        r"\s*❓",
        "\n\n❓",
        text
    )


    # 번호 뒤 장소명 처리
    text = re.sub(
        r"(①|②|③|④|⑤)\s*",
        r"\1 ",
        text
    )


    # 불필요한 공백 제거
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )


    return text.strip()

# .env 로드
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str


def get_or_create_session(db: Session, session_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)

    if session is None:
        session = ChatSession(session_id=session_id)
        db.add(session)
        db.commit()
        db.refresh(session)

    return session


def build_history_block(session: ChatSession, recent_messages: list[ChatMessage]) -> str:
    block = ""

    if session.summary:
        block += f"[이전 대화 요약]\n{session.summary}\n\n"

    if recent_messages:
        turns = "\n".join(
            f"{'사용자' if m.role == 'user' else 'AI'}: {m.content}"
            for m in recent_messages
        )
        block += f"[최근 대화]\n{turns}\n\n"

    return block


def summarize_dropped_messages(old_summary: Optional[str], dropped_messages: list[ChatMessage]) -> str:
    dropped_text = "\n".join(
        f"{'사용자' if m.role == 'user' else 'AI'}: {m.content}"
        for m in dropped_messages
    )

    prompt = f"""아래는 챗봇과 사용자의 오래된 대화입니다. 기존 요약에 이 대화의 핵심만 반영해 업데이트하세요.

규칙:
- 3문장, 200자 이내로 작성
- 사용자가 원했던 것과 언급된 장소/키워드 등 핵심 정보만 남긴다
- 마크다운, 이모지, 번호 기호를 쓰지 않는다

기존 요약:
{old_summary or "(없음)"}

오래된 대화:
{dropped_text}

업데이트된 요약:"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text.strip()


def rollover_old_turns(db: Session, session: ChatSession) -> None:
    max_messages = HISTORY_TURN_LIMIT * 2

    total = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .count()
    )

    if total <= max_messages:
        return

    dropped = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.id.asc())
        .limit(total - max_messages)
        .all()
    )

    session.summary = summarize_dropped_messages(session.summary, dropped)

    for message in dropped:
        db.delete(message)

    db.commit()


SYSTEM_PROMPT = """
너는 딸깍 AI이다.

역할:
- 대전·충청권 관광 안내 AI
- 사용자의 질문 의도를 먼저 판단한다. (단, 이 판단은 내부적으로만 하고 "의도 파악" 같은 분석 과정이나 문구는 답변에 절대 출력하지 않는다)

규칙:

1. 관광 관련 질문이면 제공된 딸깍 데이터만 사용한다.
2. 데이터에 없는 장소를 추가하지 않는다.
3. 최대 5개 장소만 추천한다.
4. 일반 질문이면 자연스럽게 답변한다.
5. 관광 질문이 아닐 때 관광지를 억지로 추천하지 않는다.
6. 최종 답변에는 사용자에게 필요한 내용만 출력한다. 의도 판단, 카테고리 분류 등 내부 처리 과정은 절대 언급하지 않는다.


========================
관광 답변 출력 규칙
========================

관광지를 추천할 때 반드시 아래 형식을 그대로 따른다.

절대 한 줄로 작성하지 않는다.

반드시 장소마다 빈 줄을 넣는다.


출력 예시:

📍 대전 숙박시설 추천


① 호텔 오노마

설명:
대전 엑스포 주변에 위치한 고급 호텔입니다.

위치:
대전광역시 유성구 엑스포로 1


② 롯데시티호텔 대전

설명:
엑스포 인근에 위치한 접근성이 좋은 호텔입니다.

위치:
대전광역시 유성구 엑스포로123번길 33


③ 호텔ICC

설명:
대전 유성구에 위치한 숙박 시설입니다.

위치:
대전광역시 유성구 엑스포로123번길 55


💡 추가 팁

방문 목적에 맞춰 위치와 가격대를 비교해 보세요.


❓ 어떤 여행 스타일인지 알려주시면 더 추천해드릴게요.


========================
금지 출력 형태
========================

절대 아래처럼 작성하지 않는다.


① 호텔 오노마 설명: 내용 위치: 주소


또는


① 호텔 오노마 - 설명 - 주소


또는


① 호텔 오노마 설명:
내용 위치:
주소


항상 장소명 / 설명 / 위치를 각각 줄바꿈한다.

"""


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_chatbot_db)):

    session_id = request.session_id or str(uuid.uuid4())
    session = get_or_create_session(db, session_id)

    recent_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_TURN_LIMIT * 2)
        .all()
    )
    recent_messages.reverse()

    history_block = build_history_block(session, recent_messages)

    last_error = None

    for attempt in range(3):

        try:

            TOUR_KEYWORDS = [
                "관광",
                "여행",
                "추천",
                "가볼",
                "명소",
                "맛집",
                "음식",
                "카페",
                "축제",
                "숙박",
                "호텔",
                "오월드",
                "성심당",
                "박물관",
                "공원"
            ]

            # 관광 관련 질문인지 판단
            use_context = any(
                keyword in request.message
                for keyword in TOUR_KEYWORDS
            )
            print(
                "USE_CONTEXT:",
                use_context,
                "MESSAGE:",
                request.message
            )

            context = ""


            # 관광 질문이면 데이터 검색
            if use_context:

                category = detect_category(request.message)

                items = load_data(category)

                items = search_items(
                    request.message,
                    items
                )

                context = build_context(items)


                user_input = f"""{history_block}
사용자 질문

{request.message}


딸깍 관광 데이터

{context}


답변 작성 규칙:

반드시 아래 형식으로 답변하세요.

① 장소명

설명:
내용

위치:
주소


② 장소명

설명:
내용

위치:
주소


장소 사이에는 반드시 빈 줄을 넣으세요.

장소명, 설명, 위치를 절대 한 줄에 작성하지 마세요.
"""

            else:

                # 일반 대화
                user_input = f"{history_block}{request.message}" if history_block else request.message



            response = client.responses.create(
                model="gpt-5-mini",
                instructions=SYSTEM_PROMPT,
                input=user_input
            )


            # ------------------ 디버깅 ------------------
            print(
                "======== CONTEXT CHECK ========"
            )
            print("MESSAGE:", request.message)
            print("USE_CONTEXT:", use_context)
            print("==============================")
            print("\n========== USER ==========")
            print(request.message)

            print("\n========== RESPONSE ==========")
            print(response.model_dump())

            print("\n========== OUTPUT_TEXT ==========")
            print(response.output_text)

            print("===============================\n")

            # --------------------------------------------


            answer = response.output_text.strip()
            print("Format before")
            print(answer)

            answer = format_answer(answer)
            print("formate after")
            print(answer)

            db.add(ChatMessage(session_id=session_id, role="user", content=request.message))
            db.add(ChatMessage(session_id=session_id, role="assistant", content=answer))
            db.commit()

            rollover_old_turns(db, session)

            return ChatResponse(
                answer=answer,
                session_id=session_id
            )


        except Exception as e:

            last_error = e

            print("CHATBOT ERROR:", e)


            if attempt < 2:
                time.sleep(2)
                continue



    return ChatResponse(
        answer=f"오류가 발생했습니다.\n{last_error}",
        session_id=session_id
    )