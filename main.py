import sys

# Windows 콘솔 기본 인코딩(cp949)이 이모지 등 일부 유니코드 문자를 출력하지 못해
# 콘솔 print()가 예외를 던지는 것을 방지합니다 (예: 챗봇 응답 디버그 출력).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# [중요] models를 먼저 import 하여 BaseCommunity 스키마 메타데이터에 Post 매핑 정보를 명시적으로 각인시킵니다.
import models
from database import community_engine, BaseCommunity, chatbot_engine, BaseChatbot
from routers import posts, locations, chatbot, comments

# 물리 디스크 볼륨(Render Disk)과 연동될 정적 이미지 폴더 경로를 생성합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PICS_DIR = os.path.join(BASE_DIR, "db_files", "pics")

# 폴더가 로컬 및 서버 환경에 아직 준비되지 않았다면 자동으로 생성합니다.
os.makedirs(PICS_DIR, exist_ok=True)
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("Checking and initializing community database tables...")
BaseCommunity.metadata.create_all(bind=community_engine)

def ensure_post_location_columns():
    """
    create_all()은 이미 존재하는 posts 테이블에 새 컬럼을 추가해주지 않으므로,
    장소 첨부 기능 도입 전에 생성된 community.db를 위해 누락된 컬럼을 직접 채워 넣습니다.
    """
    new_columns = {
        "place_title": "VARCHAR",
        "place_addr": "VARCHAR",
        "place_mapx": "VARCHAR",
        "place_mapy": "VARCHAR",
    }
    with community_engine.begin() as conn:
        existing_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(posts)")}
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                conn.exec_driver_sql(f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}")

ensure_post_location_columns()

print("Checking and initializing chatbot database tables...")
BaseChatbot.metadata.create_all(bind=chatbot_engine)

app = FastAPI(
    title="딸깍 - 대전/충청 정보 공유 플랫폼",
    description="익명 자유게시판 CRUD API 및 대전 공공데이터 조회용 API 서비스",
    version="1.0.0"
)

# Vue.js 프론트엔드가 백엔드 API에 접속 가능하도록 포트 및 오리진 CORS 전체 개방
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 개발 및 Netlify 배포 환경 대응
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [추가] 프론트엔드에서 업로드한 이미지를 조회할 수 있도록 '/pics' 주소 경로를 물리 pics 폴더와 마운트합니다.
app.mount("/pics", StaticFiles(directory=PICS_DIR), name="pics")

# API 명세서에 정의된 공통 '/api' prefix를 기준으로 라우터를 병합합니다.
app.include_router(posts.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(comments.router, prefix="/api")

@app.get("/")
def read_root():
    """
    서버 활성화 확인용 엔드포인트
    """
    return {
        "status": "healthy",
        "service": "딸깍 Backend Server",
        "docs_url": "/docs"
    }