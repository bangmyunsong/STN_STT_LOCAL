# admin_handlers.py 수정사항

# 1. import 추가 (라인 6)
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Form

# 2. upload_file 함수 수정 (라인 767-771)
@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(..., description="업로드할 음성 파일"),
    target_date: Optional[str] = Form(None, description="대상 날짜 (YYYY-MM-DD 형식)")
):
    """음성 파일을 특정 날짜 폴더에 업로드"""
    try:
        # 디버깅: 받은 파라미터 확인
        logger.info(f"업로드 요청 - 파일: {file.filename}, target_date: {target_date}")
        
        # 파일 확장자 검증
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}"
            )
        
        # 대상 날짜 설정 (기본값: 오늘)
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"target_date가 None이므로 오늘 날짜 사용: {target_date}")
        else:
            logger.info(f"전달받은 target_date 사용: {target_date}")
        
        # 대상 폴더 경로 생성
        target_folder = os.path.join(AUDIO_DIRECTORY, target_date)
        
        # 폴더가 없으면 생성
        if not os.path.exists(target_folder):
            os.makedirs(target_folder, exist_ok=True)
            logger.info(f"폴더 생성: {target_folder}")
        
        # 파일 저장 경로
        file_path = os.path.join(target_folder, file.filename)
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"파일 업로드 완료: {file_path}")
        
        return {
            "status": "success",
            "message": f"파일이 성공적으로 업로드되었습니다: {file.filename}",
            "file_path": file_path,
            "target_date": target_date,
            "file_size": os.path.getsize(file_path),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")
