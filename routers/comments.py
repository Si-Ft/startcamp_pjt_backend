from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_community_db
from models import Post, Comment

router = APIRouter(prefix="/posts", tags=["Comments"])


class CommentCreateRequest(BaseModel):
    content: str = Field(..., description="댓글 내용")
    password: str = Field(..., description="수정 및 삭제 권한용 비밀번호")


class CommentDeleteRequest(BaseModel):
    password: str = Field(..., example="1234")


class CommentResponse(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


def get_post_or_404(post_id: int, db: Session) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    return post


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
def read_comments(post_id: int, db: Session = Depends(get_community_db)):
    """
    특정 게시글에 달린 댓글을 오래된 순으로 조회합니다.
    """
    get_post_or_404(post_id, db)

    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.id.asc())
        .all()
    )


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(post_id: int, body: CommentCreateRequest, db: Session = Depends(get_community_db)):
    """
    게시글에 익명 댓글을 작성합니다.
    """
    get_post_or_404(post_id, db)

    comment = Comment(post_id=post_id, content=body.content, password=body.password)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/{post_id}/comments/{comment_id}", response_model=dict)
def delete_comment(post_id: int, comment_id: int, body: CommentDeleteRequest, db: Session = Depends(get_community_db)):
    """
    비밀번호가 일치하는 경우, 댓글을 삭제합니다.
    """
    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.post_id == post_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

    if comment.password != body.password:
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")

    db.delete(comment)
    db.commit()

    return {"message": "댓글이 삭제되었습니다"}
