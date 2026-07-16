# 백엔드 배포 시 해야할 것

1. Render 관리자 페이지 설정에서 'Disk' (Persistent Volume) 옵션을 추가하여 특정 폴더(예: /data)를 영구 저장소로 바인딩해야 합니다.

2. Render 대시보드의 Environment 탭으로 이동하여 로컬 .env에 적었던 변수명(OPENAI_API_KEY, DATABASE_URL_COMMUNITY 등)과 실제 값을 일일이 수동으로 등록해 주어야 합니다.  