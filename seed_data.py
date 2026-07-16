import os
import json
import glob
from database import daejeon_engine, DaejeonSessionLocal, BaseDaejeon
from models import Attraction

def seed_daejeon_data():
    # 1. daejeon.db 테이블 생성
    print("Initializing SQLite daejeon.db tables...")
    BaseDaejeon.metadata.create_all(bind=daejeon_engine)

    # 2. backend/data 폴더 아래에 있는 JSON 파일 검색
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    json_pattern = os.path.join(data_dir, "대전_충청권_*.json")
    json_files = glob.glob(json_pattern)

    if not json_files:
        print(f"❌ Error: {data_dir} 경로에 '대전_충청권_*.json' 파일이 없습니다.")
        print("공공데이터 JSON 파일들을 해당 폴더에 먼저 넣고 다시 실행해 주세요.")
        return

    db = DaejeonSessionLocal()
    try:
        print(f"Found {len(json_files)} JSON files. Seeding started...")
        total_inserted = 0

        for file_path in json_files:
            file_name = os.path.basename(file_path)
            print(f"👉 Processing: {file_name}")

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = data.get("items", [])
            attractions_to_insert = []

            for item in items:
                content_id = item.get("contentid")
                if not content_id:
                    continue

                # 중복 데이터 검사 (이미 존재하면 건너뜀)
                existing = db.query(Attraction).filter(Attraction.contentid == content_id).first()
                if existing:
                    continue

                # JSON 카멜케이스(cpyrhtDivCd)를 DB 스네이크케이스(cpyrht_div_cd)에 매칭
                attraction = Attraction(
                    contentid=content_id,
                    contenttypeid=item.get("contenttypeid"),
                    title=item.get("title"),
                    addr1=item.get("addr1") or None,
                    addr2=item.get("addr2") or None,
                    tel=item.get("tel") or None,
                    mapx=item.get("mapx"),
                    mapy=item.get("mapy"),
                    firstimage=item.get("firstimage") or None,
                    cpyrht_div_cd=item.get("cpyrhtDivCd") or None,
                    createdtime=item.get("createdtime"),
                    modifiedtime=item.get("modifiedtime")
                )
                attractions_to_insert.append(attraction)

            if attractions_to_insert:
                db.bulk_save_objects(attractions_to_insert)
                db.commit()
                total_inserted += len(attractions_to_insert)
                print(f"   Successfully inserted {len(attractions_to_insert)} items.")
            else:
                print("   All items in this file are already seeded or duplicate.")

        print(f"🎉 Seeding Complete! Total {total_inserted} items stored in daejeon.db")

    except Exception as e:
        db.rollback()
        print(f"❌ Database Seeding Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_daejeon_data()