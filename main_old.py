from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import posts, locations, chatbot

app = FastAPI(title="LocalHub API")

# CORS 설정 (프론트엔드 Vue.js와의 통신을 위함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 개발 단계에서는 모두 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 세 명의 라우터를 미리 연결해 둡니다. (각 파일에 빈 APIRouter가 있어야 에러가 안 납니다)
app.include_router(posts.router, prefix="/api", tags=["Posts"])
app.include_router(locations.router, prefix="/api", tags=["Locations"])
app.include_router(chatbot.router, prefix="/api", tags=["Chatbot"])

@app.get("/")
def read_root():
    return {"message": "LocalHub API Server is running!"}