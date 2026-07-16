import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 파일을 파싱하여 프로세스 환경 변수로 주입합니다.
load_dotenv()

# 실행 경로에 영향받지 않도록 현재 database.py의 절대 위치를 바탕으로 db_files 폴더 경로를 빌드합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db_files")

# 만약 db_files 디렉터리가 로컬 환경에 생성되지 않았다면 안전하게 폴더를 자동 빌드합니다.
os.makedirs(DB_DIR, exist_ok=True)

# 절대 경로가 매핑된 3개의 SQLite DB URL 설정
DB_URL_DAEJEON = os.getenv("DATABASE_URL_DAEJEON", f"sqlite:///{os.path.join(DB_DIR, 'daejeon.db')}")
DB_URL_COMMUNITY = os.getenv("DATABASE_URL_COMMUNITY", f"sqlite:///{os.path.join(DB_DIR, 'community.db')}")
DB_URL_CHATBOT = os.getenv("DATABASE_URL_CHATBOT", f"sqlite:///{os.path.join(DB_DIR, 'chatbot.db')}")

# 동시성 처리를 위해 check_same_thread=False를 지정하여 SQLite 멀티스레드를 연동합니다.
daejeon_engine = create_engine(DB_URL_DAEJEON, connect_args={"check_same_thread": False})
community_engine = create_engine(DB_URL_COMMUNITY, connect_args={"check_same_thread": False})
chatbot_engine = create_engine(DB_URL_CHATBOT, connect_args={"check_same_thread": False})

DaejeonSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=daejeon_engine)
CommunitySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=community_engine)
ChatbotSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=chatbot_engine)

# 각 데이터베이스 테이블 스키마가 분할 저장될 수 있도록 베이스 객체를 선언합니다.
BaseDaejeon = declarative_base()
BaseCommunity = declarative_base()
BaseChatbot = declarative_base()

# API 통신 완료 시 트랜잭션을 세션과 함께 커넥션 풀에 안전하게 자동 반환 처리합니다.
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