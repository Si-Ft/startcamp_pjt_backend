from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship  # 💡 1:N 테이블 매핑 및 관계 정의를 위해 추가 임포트
from database import BaseDaejeon, BaseCommunity, BaseChatbot

# ==========================================
# 1. 대전데이터 DB (daejeon.db) 테이블
# ==========================================
class Attraction(BaseDaejeon):
    __tablename__ = "attractions"

    contentid = Column(String, primary_key=True, index=True)
    contenttypeid = Column(String, index=True, nullable=False) # 12관광지, 14문화시설, 15축제 등
    title = Column(String, nullable=False)
    addr1 = Column(String, nullable=True)
    addr2 = Column(String, nullable=True)
    tel = Column(String, nullable=True)
    mapx = Column(String, nullable=True) # 경도 (string 보존)
    mapy = Column(String, nullable=True) # 위도 (string 보존)
    firstimage = Column(String, nullable=True)
    cpyrht_div_cd = Column(String, nullable=True) # 공공누리 유형 (cpyrhtDivCd 변환 저장)
    createdtime = Column(String, nullable=True)
    modifiedtime = Column(String, nullable=True)


# ==========================================
# 2. 커뮤니티 DB (community.db) 테이블
# ==========================================
class Post(BaseCommunity):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, index=True, nullable=False) # 맛집, 관광지, 숙박 등
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    password = Column(String, nullable=False) # 수정용 평문 패스워드
    view_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 게시글에 선택적으로 첨부하는 장소 정보 (지도에서 좌표를 찍고 주소는 역지오코딩으로 채움)
    place_title = Column(String, nullable=True)
    place_addr = Column(String, nullable=True)
    place_mapx = Column(String, nullable=True)  # 경도
    place_mapy = Column(String, nullable=True)  # 위도

    # [추가] 1:N 관계 매핑 - 게시글이 삭제되면 데이터베이스 내의 연결 이미지 목록/댓글도 자동 삭제(cascade)되도록 설정합니다.
    images = relationship("PostImage", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class PostImage(BaseCommunity):
    __tablename__ = "post_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    image_name = Column(String, nullable=False)  # UUID 난수화 처리 후 물리 디스크에 저장될 중복 없는 파일명

    # [추가] 역방향 참조 설정
    post = relationship("Post", back_populates="images")


class Comment(BaseCommunity):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    password = Column(String, nullable=False)  # 수정용 평문 패스워드 (게시글과 동일한 익명 방식)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="comments")


# ==========================================
# 3. 챗봇 DB (chatbot.db) 테이블
# ==========================================
class ChatSession(BaseChatbot):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)  # 프론트에서 발급한 UUID
    summary = Column(Text, nullable=True)  # 5턴보다 오래된 대화의 누적 요약
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(BaseChatbot):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")