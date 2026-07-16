from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# DB 설정 및 SQLAlchemy 테이블 마이그레이션 모듈 불러오기
from database import community_engine, BaseCommunity
from routers import posts, locations, chatbot

# 서버 기동 시 community.db 파일 및 posts 테이블이 아직 없다면 자동으로 물리 설계 테이블을 구축합니다.
print("Checking and initializing community database tables...")
BaseCommunity.metadata.create_all(bind=community_engine)

app = FastAPI(
    title="LocalHub - 대전/충청 정보 공유 플랫폼",
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

# API 명세서에 정의된 공통 '/api' prefix를 기준으로 라우터를 병합합니다.
app.include_router(posts.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "LocalHub Backend Server",
        "docs_url": "/docs"
    }