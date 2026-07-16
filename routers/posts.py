import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_community_db
from models import Post, PostImage, Comment

router = APIRouter(prefix="/posts", tags=["Community Posts"])

# backend/db_files/pics 디렉터리의 절대 경로를 설정합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICS_DIR = os.path.join(BASE_DIR, "db_files", "pics")

class PostImageResponse(BaseModel):
    id: int
    image_name: str

    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: int
    category: str
    title: str
    content: str
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    images: List[PostImageResponse] = []  # 게시글 조회 시 업로드된 이미지 리스트를 함께 내려줍니다.
    place_title: Optional[str] = None
    place_addr: Optional[str] = None
    place_mapx: Optional[str] = None
    place_mapy: Optional[str] = None

    class Config:
        from_attributes = True

class PostListItemResponse(BaseModel):
    id: int
    category: str
    title: str
    images: List[PostImageResponse] = []  # 목록에서도 썸네일 렌더링을 위해 상세와 동일하게 이미지 리스트를 내려줍니다.
    view_count: int
    like_count: int
    created_at: datetime
    comment_count: int = 0
    place_title: Optional[str] = None
    place_addr: Optional[str] = None

    class Config:
        from_attributes = True

class PaginatedPostList(BaseModel):
    total: int
    page: int
    size: int
    items: List[PostListItemResponse]

class PostDeleteRequest(BaseModel):
    password: str = Field(..., example="1234")


SORT_OPTIONS = {
    "latest": Post.id.desc(),
    "likes": Post.like_count.desc(),
    "views": Post.view_count.desc(),
    "popular": (Post.like_count * 5 + Post.view_count).desc()  # 좋아요를 조회수보다 더 적극적인 신호로 취급해 가중치 부여
}

@router.get("", response_model=PaginatedPostList)
def read_posts(
    category: Optional[str] = Query(None, description="카테고리 필터 (예: 맛집, 관광지)"),
    keyword: Optional[str] = Query(None, description="제목 및 본문 검색어"),
    sort: str = Query("latest", description="정렬 기준: latest(최신순), likes(좋아요순), views(조회순)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지당 개수"),
    db: Session = Depends(get_community_db)
):
    """
    게시글 목록을 페이징하여 조회합니다.
    """
    query = db.query(Post)

    if category:
        query = query.filter(Post.category == category)

    if keyword:
        query = query.filter(
            or_(
                Post.title.like(f"%{keyword}%"),
                Post.content.like(f"%{keyword}%")
            )
        )

    total = query.count()
    offset = (page - 1) * size
    posts = (
        query.options(selectinload(Post.images))
        .order_by(SORT_OPTIONS.get(sort, Post.id.desc()), Post.id.desc())  # id를 2차 정렬 기준으로 둬 동점일 때 페이지네이션이 안정적으로 유지되도록 함
        .offset(offset)
        .limit(size)
        .all()
    )

    # 댓글 전체를 불러오지 않고 post_id별 개수만 별도 쿼리로 집계 (N+1 방지)
    post_ids = [post.id for post in posts]
    comment_counts = dict(
        db.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
        .all()
    ) if post_ids else {}

    for post in posts:
        post.comment_count = comment_counts.get(post.id, 0)

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": posts
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_post(
    category: str = Form(..., description="카테고리 (예: 맛집)"),
    title: str = Form(..., description="게시글 제목"),
    content: str = Form(..., description="게시글 본문"),
    password: str = Form(..., description="수정 및 삭제 권한용 비밀번호"),
    files: Optional[List[UploadFile]] = File(None, description="다중 업로드 이미지 파일 리스트"),
    place_title: Optional[str] = Form(None, description="첨부한 장소명 (선택)"),
    place_addr: Optional[str] = Form(None, description="첨부한 장소 주소 (선택)"),
    place_mapx: Optional[str] = Form(None, description="첨부한 장소 경도 (선택)"),
    place_mapy: Optional[str] = Form(None, description="첨부한 장소 위도 (선택)"),
    db: Session = Depends(get_community_db)
):
    """
    텍스트 데이터와 업로드된 다중 이미지 파일을 한 번에 받아 저장합니다.
    (Content-Type: multipart/form-data 가 적용됩니다.)
    """
    # 1. 파일 이름 난수화 및 물리적 로컬 저장 처리
    saved_images = []
    if files:
        for file in files:
            # 빈 파일 객체 필터링
            if not file.filename:
                continue
            
            # 원본 확장자 분리 (예: .png)
            ext = os.path.splitext(file.filename)[1]
            # UUID를 활용해 중복 확률이 없는 유일무이한 파일명으로 치환
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(PICS_DIR, unique_filename)

            # 디스크 볼륨(pics 폴더)에 바이너리 데이터 물리 기록
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_images.append(unique_filename)

    # 2. 데이터베이스에 게시글(Post) 생성 및 이미지 릴레이션 매핑 기록
    new_post = Post(
        category=category,
        title=title,
        content=content,
        password=password,
        view_count=0,
        like_count=0,
        place_title=place_title or None,
        place_addr=place_addr or None,
        place_mapx=place_mapx or None,
        place_mapy=place_mapy or None
    )
    db.add(new_post)
    db.flush()  # DB 상의 id 값을 먼저 선점하기 위해 flush 합니다.

    # 3. 이미지 테이블 관계 주입
    for img_name in saved_images:
        db_img = PostImage(post_id=new_post.id, image_name=img_name)
        db.add(db_img)

    db.commit()
    db.refresh(new_post)

    return {
        "id": new_post.id,
        "message": "이미지를 포함한 게시글이 성공적으로 등록되었습니다."
    }


@router.get("/{post_id}", response_model=PostResponse)
def read_post_detail(post_id: int, db: Session = Depends(get_community_db)):
    """
    특정 게시글의 세부 정보와 1:N으로 업로드된 이미지 파일 리스트를 한 번에 조회합니다.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    
    # 상세 조회 성공 시 조회수 1 증가
    post.view_count += 1
    db.commit()
    db.refresh(post)
    
    return post


@router.put("/{post_id}", response_model=dict)
def update_post(
    post_id: int,
    title: str = Form(..., example="수정된 제목"),
    content: str = Form(..., example="수정된 본문"),
    password: str = Form(..., example="1234"),
    files: Optional[List[UploadFile]] = File(None, description="새로 추가할 이미지 파일 리스트"),
    place_title: Optional[str] = Form(None, description="첨부한 장소명 (선택)"),
    place_addr: Optional[str] = Form(None, description="첨부한 장소 주소 (선택)"),
    place_mapx: Optional[str] = Form(None, description="첨부한 장소 경도 (선택)"),
    place_mapy: Optional[str] = Form(None, description="첨부한 장소 위도 (선택)"),
    db: Session = Depends(get_community_db)
):
    """
    비밀번호가 일치하는 경우, 게시글의 본문 정보를 수정합니다.
    (Content-Type: multipart/form-data - create_post와 동일한 방식)
    기존에 첨부된 이미지는 그대로 유지되며, files로 전달된 이미지는 추가로 첨부됩니다.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    if post.password != password:
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")

    post.title = title
    post.content = content
    post.updated_at = datetime.now()
    post.place_title = place_title or None
    post.place_addr = place_addr or None
    post.place_mapx = place_mapx or None
    post.place_mapy = place_mapy or None

    if files:
        for file in files:
            if not file.filename:
                continue

            ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(PICS_DIR, unique_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            db.add(PostImage(post_id=post.id, image_name=unique_filename))

    db.commit()
    return {"message": "게시글이 성공적으로 수정되었습니다."}


@router.delete("/{post_id}", response_model=dict)
def delete_post(post_id: int, request_body: PostDeleteRequest, db: Session = Depends(get_community_db)):
    """
    비밀번호 인증 성공 시, DB 테이블 데이터 뿐만 아니라 디스크 상에 남아있는 실제 이미지 파일들도 완전히 연동하여 추적 삭제합니다.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    
    if post.password != request_body.password:
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
    
    # 물리적 디스크 이미지 정리 로직
    # 데이터베이스가 지워지기 전에 연동된 사진들의 실물 위치를 읽어 영구 보관용 폴더에서 직접 지워줍니다.
    for img in post.images:
        physical_path = os.path.join(PICS_DIR, img.image_name)
        if os.path.exists(physical_path):
            try:
                os.remove(physical_path)
            except Exception as e:
                # 삭제 도중 권한 오류 등이 발생해도 다음 전체 진행을 망치지 않게 로깅만 남겨둡니다.
                print(f"[Warning] Failed to delete physical image file {physical_path}: {e}")

    db.delete(post)
    db.commit()
    
    return {"message": "게시글과 디스크 내 물리 이미지가 모두 안전하게 영구 삭제되었습니다."}


@router.post("/{post_id}/like", response_model=dict)
def like_post(post_id: int, db: Session = Depends(get_community_db)):
    """
    게시글의 좋아요 카운트를 1 증가시킵니다.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    
    post.like_count += 1
    db.commit()
    db.refresh(post)
    
    return {"like_count": post.like_count}