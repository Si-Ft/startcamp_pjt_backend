from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

# database 및 models 연동
from database import get_daejeon_db
from models import Attraction

router = APIRouter(prefix="/locations", tags=["Daejeon Public Data"])

class AttractionResponse(BaseModel):
    contentid: str
    contenttypeid: str
    title: str
    addr1: Optional[str] = None
    addr2: Optional[str] = None
    tel: Optional[str] = None
    mapx: Optional[str] = None
    mapy: Optional[str] = None
    firstimage: Optional[str] = None
    cpyrht_div_cd: Optional[str] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None

    class Config:
        from_attributes = True

class PaginatedAttractionList(BaseModel):
    total: int
    page: int
    size: int
    items: List[AttractionResponse]

@router.get("", response_model=PaginatedAttractionList)
def get_attractions(
    contenttypeid: Optional[str] = Query(None, description="콘텐츠 타입 ID (12:관광지, 14:문화시설, 15:축제, 32:숙박, 39:음식점 등)"),
    keyword: Optional[str] = Query(None, description="장소명 또는 주소 검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지당 개수"),
    db: Session = Depends(get_daejeon_db)
):
    """
    대전_충청권 공공데이터(attractions) 테이블을 필터링 및 검색 조회합니다.
    """
    query = db.query(Attraction)

    # 콘텐츠 타입 필터 (예: 39:음식점)
    if contenttypeid:
        query = query.filter(Attraction.contenttypeid == contenttypeid)

    # 키워드 필터 (이름 또는 주소)
    if keyword:
        query = query.filter(
            Attraction.title.like(f"%{keyword}%") | 
            Attraction.addr1.like(f"%{keyword}%")
        )

    # 전체 데이터 개수 카운팅
    total = query.count()

    # 페이징 적용하여 조회
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }

class MapPinResponse(BaseModel):
    contentid: str
    contenttypeid: str
    title: str
    addr1: Optional[str] = None
    mapx: Optional[str] = None
    mapy: Optional[str] = None
    firstimage: Optional[str] = None

    class Config:
        from_attributes = True

# 한국 영토를 벗어나는 좌표(원본 TourAPI 데이터의 좌표 오기입)를 걸러내기 위한 대략적인 경계
KOREA_LAT_RANGE = (33.0, 39.0)
KOREA_LNG_RANGE = (124.0, 132.0)

# 한국 영토 범위 안이지만 실제 주소와 동떨어진 좌표로 확인된 항목(경계값 필터로는 못 거름)
KNOWN_BAD_CONTENT_IDS = {
    "128113",  # 공주 우금치 전적 - 주소는 공주시인데 좌표는 평택 인근을 가리킴
}

def _has_valid_korea_coords(item: Attraction) -> bool:
    if item.contentid in KNOWN_BAD_CONTENT_IDS:
        return False

    try:
        lat = float(item.mapy)
        lng = float(item.mapx)
    except (TypeError, ValueError):
        return False

    return (
        KOREA_LAT_RANGE[0] <= lat <= KOREA_LAT_RANGE[1]
        and KOREA_LNG_RANGE[0] <= lng <= KOREA_LNG_RANGE[1]
    )

@router.get("/map", response_model=List[MapPinResponse])
def get_map_pins(
    contenttypeid: Optional[str] = Query(None, description="콘텐츠 타입 ID로 필터링"),
    db: Session = Depends(get_daejeon_db)
):
    """
    지도 핀 시각화용 - 좌표가 있는 장소를 페이징 없이 전량 반환합니다.
    """
    query = db.query(Attraction).filter(
        Attraction.mapx.isnot(None),
        Attraction.mapy.isnot(None)
    )

    if contenttypeid:
        query = query.filter(Attraction.contenttypeid == contenttypeid)

    return [item for item in query.all() if _has_valid_korea_coords(item)]

@router.get("/random", response_model=List[AttractionResponse])
def get_random_attractions(
    contenttypeid: Optional[str] = Query(None, description="콘텐츠 타입 ID로 필터링"),
    size: int = Query(30, ge=1, le=100, description="가져올 개수"),
    db: Session = Depends(get_daejeon_db)
):
    """
    홈 화면 카테고리 브라우징용 - 사진이 있는 장소 중 무작위로 size개를 반환합니다.
    (방문할 때마다 다른 장소가 보이도록 매 요청마다 새로 무작위 추출)
    """
    query = db.query(Attraction).filter(
        Attraction.firstimage.isnot(None),
        Attraction.firstimage != "",
        Attraction.addr1.isnot(None)
    )

    if contenttypeid:
        query = query.filter(Attraction.contenttypeid == contenttypeid)

    return query.order_by(func.random()).limit(size).all()

@router.get("/{content_id}", response_model=AttractionResponse)
def get_attraction_detail(content_id: str, db: Session = Depends(get_daejeon_db)):
    """
    공공데이터 테이블에서 contentid가 일치하는 특정 장소 상세 정보를 가져옵니다.
    """
    item = db.query(Attraction).filter(Attraction.contentid == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 장소 데이터를 찾을 수 없습니다")
    return item