import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# DB 파일이 저장될 db_files 디렉터리 자동 생성
os.makedirs("./db_files", exist_ok=True)

# 1. DB 환경 변수 가져오기 (디렉터리 내부로 기본값 매핑)
DB_URL_DAEJEON = os.getenv("DATABASE_URL_DAEJEON", "sqlite:///./db_files/daejeon.db")
DB_URL_COMMUNITY = os.getenv("DATABASE_URL_COMMUNITY", "sqlite:///./db_files/community.db")
DB_URL_CHATBOT = os.getenv("DATABASE_URL_CHATBOT", "sqlite:///./db_files/chatbot.db")

# 2. 개별 Engine 생성 (SQLite 동시 스레드 허용 설정 적용)
daejeon_engine = create_engine(DB_URL_DAEJEON, connect_args={"check_same_thread": False})
community_engine = create_engine(DB_URL_COMMUNITY, connect_args={"check_same_thread": False})
chatbot_engine = create_engine(DB_URL_CHATBOT, connect_args={"check_same_thread": False})

# 3. 개별 SessionLocal 생성
DaejeonSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=daejeon_engine)
CommunitySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=community_engine)
ChatbotSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=chatbot_engine)

# 4. 멀티 DB용 Declarative Base 분리 선언
BaseDaejeon = declarative_base()
BaseCommunity = declarative_base()
BaseChatbot = declarative_base()

# 5. FastAPI에서 사용할 DB 의존성 주입 (Dependency) 함수들
def get_daejeon_db():
    db = DaejeonSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_community_db():
    db = CommunitySessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_chatbot_db():
    db = ChatbotSessionLocal()
    try:
        yield db
    finally:
        db.close()