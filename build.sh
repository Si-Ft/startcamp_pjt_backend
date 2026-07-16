# backend Render 배포 시 실행 코드

# 에러 발생 시 즉시 종료 옵션 코드
set -o errexit

# 1. 파이썬 의존성 패키지 설치
pip install -r requirements.txt

DB_DIR="./db_files"
DAEJEON_DB="$DB_DIR/daejeon.db"

# 2. Render 서버가 켜질 때 공공데이터가 없으면 자동으로 데이터베이스에 적재하도록 실행
if [ ! -f "$DAEJEON_DB" ]; then
echo "⚡ [INIT] daejeon.db 파일이 존재하지 않습니다. 최초 1회 공공데이터 적재를 시작합니다..."
python seed_data.py
echo "✅ [SUCCESS] 공공데이터 적재가 완료되었습니다."
else
echo "ℹ️ [SKIP] 이미 daejeon.db 파일이 영구 디스크에 존재하므로 데이터 적재를 건너뜁니다."
fi