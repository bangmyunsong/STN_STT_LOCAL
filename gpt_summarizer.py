"""
GPT-4o 기반 요약 및 요청사항 분석 클래스
패턴 매칭 대신 GPT-4o를 사용하여 더 정확한 요약과 분석을 제공
"""

import openai
import os
from typing import Dict, Optional
import logging
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv('config.env')

logger = logging.getLogger(__name__)

class GPT4oSummarizer:
    """GPT-4o 기반 요약 및 요청사항 분석 클래스"""
    
    def __init__(self):
        """GPT-4o 요약기 초기화"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key or self.api_key == 'your_openai_api_key_here':
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. config.env 파일을 확인하세요.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model_name = os.getenv('GPT_MODEL', 'gpt-4o')
        self.use_gpt4o = os.getenv('USE_GPT4O_SUMMARY', 'false').lower() == 'true'
        
        logger.info(f"GPT-4o 요약기 초기화 완료 - 모델: {self.model_name}, 사용여부: {self.use_gpt4o}")
    
    def create_enhanced_summary(self, transcript: str, erp_data: dict) -> str:
        """
        GPT-4o로 향상된 요약 생성
        기존 패턴 매칭 대신 GPT-4o의 향상된 이해력을 활용
        """
        if not self.use_gpt4o:
            logger.info("GPT-4o 요약 비활성화됨, 패턴 매칭으로 폴백")
            return self._fallback_summary(transcript, erp_data)
        
        try:
            system_prompt = """당신은 고객센터 통화 내용을 분석하여 ERP 시스템용 요약을 생성하는 전문가입니다.

다음 형식으로 요약해주세요:
[요약] [요청기관] [AS 및 지원] 요청
[유형] [요청유형] | [분석된 요청유형]
[위치] [작업국소] | [추출된 시간/장소]
[문제] [추출된 문제 정보]
[핵심] [핵심 문장들]

요약 규칙:
- 고객센터 통화의 핵심 내용만 추출
- 기술적 용어와 업무 맥락을 정확히 파악
- 요청의 긴급성과 중요도를 판단
- 구체적인 장비명, 위치, 시간 정보 포함
- 간결하고 명확하게 작성
- 한국어로 작성"""

            user_prompt = f"""다음 고객센터 통화 내용을 분석하여 요약해주세요:

**통화 내용:**
{transcript}

**추출된 ERP 정보:**
- AS 및 지원: {erp_data.get('AS 및 지원', '정보 없음')}
- 요청기관: {erp_data.get('요청기관', '정보 없음')}
- 작업국소: {erp_data.get('작업국소', '정보 없음')}
- 요청유형: {erp_data.get('요청유형', '정보 없음')}

위 정보를 바탕으로 구조화된 요약을 생성해주세요."""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=800  # 요약이 더 길어질 수 있으므로 증가
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info("GPT-4o 요약 생성 완료")
            return summary
            
        except Exception as e:
            logger.error(f"GPT-4o 요약 생성 실패: {e}")
            # 폴백: 기존 패턴 매칭 사용
            return self._fallback_summary(transcript, erp_data)
    
    def analyze_request_context_gpt4o(self, conversation_text: str, stn_data: dict) -> str:
        """
        GPT-4o로 요청사항 문맥 분석
        기존 패턴 매칭 대신 GPT-4o의 향상된 분석 능력 활용
        """
        if not self.use_gpt4o:
            logger.info("GPT-4o 요청사항 분석 비활성화됨, 패턴 매칭으로 폴백")
            return self._fallback_request_analysis(conversation_text, stn_data)
        
        try:
            system_prompt = """당신은 고객센터 통화에서 고객의 요청사항을 정확히 파악하는 전문가입니다.

다음 정보를 추출해주세요:
1. 구체적인 요청 내용
2. 긴급성 수준
3. 관련 장비/시스템 정보
4. 시간/위치 정보
5. 후속 조치 요청사항

분석 규칙:
- 고객이 실제로 요청한 구체적인 내용 중심으로 분석
- 기술적 맥락과 업무 상황을 고려
- 간결하고 명확하게 요청사항 정리
- 한국어로 작성"""

            user_prompt = f"""다음 고객센터 통화에서 고객의 요청사항을 분석해주세요:

**통화 내용:**
{conversation_text}

**기본 ERP 정보:**
- 장애유형: {stn_data.get('장애유형', '정보 없음')}
- 요청유형: {stn_data.get('요청유형', '정보 없음')}

고객이 실제로 요청한 구체적인 내용을 분석해주세요."""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=600
            )
            
            request_context = response.choices[0].message.content.strip()
            logger.info("GPT-4o 요청사항 분석 완료")
            return request_context
            
        except Exception as e:
            logger.error(f"GPT-4o 요청사항 분석 실패: {e}")
            # 폴백: 기존 패턴 매칭 사용
            return self._fallback_request_analysis(conversation_text, stn_data)
    
    def _fallback_summary(self, transcript: str, erp_data: dict) -> str:
        """폴백: 기존 패턴 매칭 요약"""
        try:
            # 기존 _create_simple_summary 로직을 여기로 이동
            import re
            
            # ERP 데이터에서 주요 정보 추출
            as_support = erp_data.get("AS 및 지원", "정보 없음")
            request_org = erp_data.get("요청기관", "정보 없음")
            request_type = erp_data.get("요청유형", "정보 없음")
            location = erp_data.get("작업국소", "정보 없음")
            
            # 1. 핵심 문장 추출 (패턴 매칭)
            key_sentences = self._extract_key_sentences(transcript)
            
            # 2. 요청 유형 분석
            request_analysis = self._analyze_request_type(transcript)
            
            # 3. 문제 상황 추출
            problem_info = self._extract_problem_info(transcript)
            
            # 4. 시간/장소 정보 추출
            time_location = self._extract_time_location(transcript)
            
            # 5. 요약 생성
            summary = f"""[요약] {request_org} {as_support} 요청
[유형] {request_type} | {request_analysis}
[위치] {location} | {time_location}
[문제] {problem_info}
[핵심] {key_sentences}"""
            
            logger.info("패턴 매칭 기반 요약 생성 완료 (폴백)")
            return summary
            
        except Exception as e:
            logger.warning(f"패턴 매칭 요약 생성 실패: {e}")
            return f"[요약] 요청 내용: {transcript[:100]}..."
    
    def _fallback_request_analysis(self, conversation_text: str, stn_data: dict) -> str:
        """폴백: 기존 패턴 매칭 분석"""
        try:
            # 기존 analyze_request_context 로직을 여기로 이동
            if not conversation_text:
                return f"장애유형: {stn_data.get('장애유형', '정보 없음')}, 요청유형: {stn_data.get('요청유형', '정보 없음')}"
            
            # 상세한 요청사항 분석
            request_details = []
            
            # 1. UPS 관련 요청사항
            if 'UPS' in conversation_text:
                if '소유권' in conversation_text or '고객 건지' in conversation_text or '저희 건지' in conversation_text:
                    request_details.append("UPS 소유권 확인 요청")
                if '교체' in conversation_text:
                    request_details.append("UPS 교체 작업 관련")
                if '설치' in conversation_text:
                    request_details.append("UPS 설치 관련 문의")
                if 'KTS가 제공하는' in conversation_text:
                    request_details.append("KTS 제공 UPS 여부 확인")
            
            # 2. 장애 상황 분석
            if '링크 장애' in conversation_text:
                request_details.append("해외 페콜망 링크 장애 발생")
            if '복구' in conversation_text and '원인 파악' in conversation_text:
                request_details.append("장애 복구 후 원인 파악 요청")
            if '알람' in conversation_text and '성능' in conversation_text:
                request_details.append("성능 관련 알람 발생")
            
            # 3. 긴급성 및 처리 요청
            if '긴급하게' in conversation_text and '확인 요청' in conversation_text:
                request_details.append("긴급 확인 및 점검 요청")
            if '부탁드릴게요' in conversation_text:
                request_details.append("기술 지원 요청")
            if '확인하고 싶어서' in conversation_text:
                request_details.append("상황 확인 요청")
            
            # 4. 구체적인 요청 내용
            if '회산번호' in conversation_text and '장비명' in conversation_text:
                request_details.append("회선번호 및 장비명 확인 요청")
            if '서버 IP' in conversation_text:
                request_details.append("서버 IP 정보 확인")
            if '연락 드리겠습니다' in conversation_text:
                request_details.append("후속 연락 및 조치 예정")
            
            # 5. 시간 및 위치 정보
            time_pattern = r'(\d{1,2}시\s*\d{0,2}분?)'
            time_matches = re.findall(time_pattern, conversation_text)
            if time_matches:
                request_details.append(f"장애 발생 시간: {time_matches[0]}")
            
            if '천안 아산' in conversation_text:
                request_details.append("천안 아산 지역 장애")
            if '인천' in conversation_text:
                request_details.append("인천 지역 관련")
            
            # 6. 장비 및 네트워크 정보
            ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            ip_matches = re.findall(ip_pattern, conversation_text)
            if ip_matches:
                request_details.append(f"대상 서버 IP: {ip_matches[0]}")
            
            if 'ROADN' in conversation_text or 'ROADM' in conversation_text:
                request_details.append("ROAD 장비 관련 이슈")
            
            # 7. 고객사 및 네트워크 정보
            if '삼성 SDS' in conversation_text:
                request_details.append("삼성 SDS 고객사")
            if '해외 페콜망' in conversation_text:
                request_details.append("해외 페콜망 관련")
            if '선관위' in conversation_text:
                request_details.append("선관위 관련")
            
            # 8. 요청자 및 후속 조치
            if '전역망원지팀' in conversation_text:
                request_details.append("전역망원지팀 요청")
            if 'CTA' in conversation_text:
                request_details.append("CTA 담당자 관련")
            
            # 요청사항 종합 정리
            if request_details:
                detailed_request = " | ".join(request_details)
                return detailed_request
            else:
                # 기본 정보만 반환
                base_info_parts = []
                if stn_data.get('장애유형') and stn_data.get('장애유형') != 'None':
                    base_info_parts.append(f"장애유형: {stn_data.get('장애유형')}")
                if stn_data.get('요청유형') and stn_data.get('요청유형') != 'None':
                    base_info_parts.append(f"요청유형: {stn_data.get('요청유형')}")
                
                return " | ".join(base_info_parts) if base_info_parts else "요청사항 정보 없음"
                
        except Exception as e:
            logger.warning(f"패턴 매칭 요청사항 분석 실패: {e}")
            return "요청사항 분석 실패"
    
    def _extract_key_sentences(self, transcript: str) -> str:
        """핵심 문장 추출 (패턴 매칭)"""
        import re
        
        # 고객 요청 관련 패턴
        request_patterns = [
            r'[가-힣]*[가-힣]*(?:문제|장애|오류|안됨|안돼|안되|고장|이상)[가-힣]*',
            r'[가-힣]*[가-힣]*(?:요청|부탁|해주세요|도와주세요|지원)[가-힣]*',
            r'[가-힣]*[가-힣]*(?:급함|급해|빨리|오늘|내일)[가-힣]*'
        ]
        
        sentences = transcript.split('.')
        key_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # 너무 짧은 문장 제외
                continue
                
            for pattern in request_patterns:
                if re.search(pattern, sentence):
                    key_sentences.append(sentence)
                    break
        
        # 최대 3개 문장만 선택
        return ' | '.join(key_sentences[:3]) if key_sentences else "핵심 문장 없음"
    
    def _analyze_request_type(self, transcript: str) -> str:
        """요청 유형 분석"""
        import re
        
        # 장애 관련 패턴
        if re.search(r'(?:장애|오류|고장|이상|안됨|안돼)', transcript):
            return "장애신고"
        
        # 기술지원 관련 패턴
        if re.search(r'(?:지원|도움|해결|수리|점검)', transcript):
            return "기술지원"
        
        # 문의 관련 패턴
        if re.search(r'(?:문의|질문|확인|알려주세요)', transcript):
            return "문의사항"
        
        # 긴급 관련 패턴
        if re.search(r'(?:급함|급해|빨리|즉시)', transcript):
            return "긴급요청"
        
        return "일반요청"
    
    def _extract_problem_info(self, transcript: str) -> str:
        """문제 상황 정보 추출"""
        import re
        
        # 장비-문제 조합 패턴
        equipment_problems = [
            (r'UPS.*(?:문제|장애|오류)', 'UPS 장비 문제'),
            (r'ROAD.*(?:문제|장애|오류)', 'ROAD 장비 문제'),
            (r'MSPP.*(?:문제|장애|오류)', 'MSPP 장비 문제'),
            (r'스위치.*(?:문제|장애|오류)', '스위치 장비 문제'),
            (r'라우터.*(?:문제|장애|오류)', '라우터 장비 문제')
        ]
        
        for pattern, description in equipment_problems:
            if re.search(pattern, transcript, re.IGNORECASE):
                return description
        
        # 일반적인 문제 패턴
        if re.search(r'(?:링크.*장애|네트워크.*문제)', transcript):
            return "네트워크 링크 장애"
        
        if re.search(r'(?:서버.*문제|시스템.*장애)', transcript):
            return "서버/시스템 장애"
        
        return "장비 문제"
    
    def _extract_time_location(self, transcript: str) -> str:
        """시간/장소 정보 추출"""
        import re
        
        # 시간 정보
        time_info = []
        time_patterns = [
            r'(\d{1,2}시\s*\d{0,2}분?)',
            r'(오늘|내일|어제)',
            r'(오전|오후|저녁)'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, transcript)
            if matches:
                time_info.extend(matches)
        
        # 장소 정보
        location_info = []
        location_patterns = [
            r'(서울|부산|대전|대구|광주|울산|인천)',
            r'(천안|아산|수원|성남|고양)',
            r'(본사|지사|센터|사무소)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, transcript)
            if matches:
                location_info.extend(matches)
        
        # 정보 조합
        info_parts = []
        if time_info:
            info_parts.append(f"시간: {', '.join(time_info[:2])}")
        if location_info:
            info_parts.append(f"장소: {', '.join(location_info[:2])}")
        
        return ' | '.join(info_parts) if info_parts else "시간/장소 정보 없음"


# 전역 GPT-4o 요약기 인스턴스
_gpt4o_summarizer: Optional[GPT4oSummarizer] = None

def get_gpt4o_summarizer() -> Optional[GPT4oSummarizer]:
    """GPT-4o 요약기 싱글톤 인스턴스를 반환합니다"""
    global _gpt4o_summarizer
    
    if _gpt4o_summarizer is None:
        try:
            _gpt4o_summarizer = GPT4oSummarizer()
        except Exception as e:
            logger.warning(f"GPT-4o 요약기 초기화 실패: {e}")
            _gpt4o_summarizer = None
    
    return _gpt4o_summarizer

