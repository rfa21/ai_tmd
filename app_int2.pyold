import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from anthropic import Anthropic
import json
import datetime
from io import BytesIO
import fitz
import os
import textwrap

# Firebase 초기화 (한 번만 실행)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 쿠키 매니저 초기화
cookies = EncryptedCookieManager(
    prefix="chatbot_",
    password=st.secrets["cookie_password"]
)

if not cookies.ready():
    st.stop()

# 사용자 ID 관리
if 'user_id' not in cookies:
    cookies['user_id'] = str(uuid.uuid4())
    cookies.save()

USER_ID = cookies['user_id']

# 페이지 설정
st.set_page_config(
    page_title="턱관절 AI 대화형 문진 시스템",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 폰트 파일 경로 설정
script_dir = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(script_dir, "NanumGothic.ttf")

# 세션 상태 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []
    
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

if 'conversation_complete' not in st.session_state:
    st.session_state.conversation_complete = False

if 'api_key_validated' not in st.session_state:
    st.session_state.api_key_validated = False

if 'anthropic_client' not in st.session_state:
    st.session_state.anthropic_client = None

# ===== 기존 진단 로직 함수 (app.py에서 가져옴) =====
def compute_diagnoses_for_all_symptoms(state):
    """선택된 모든 증상에 대해 진단을 수행"""
    diagnoses = []
    selected_symptoms = state.get("selected_symptoms", [])
    
    def is_yes(val): 
        if isinstance(val, str):
            return val.lower() in ["예", "yes", "y", "네", "맞아요", "그렇습니다"]
        return val == "예"
    
    def is_no(val): 
        if isinstance(val, str):
            return val.lower() in ["아니오", "no", "n", "아니요", "아닙니다"]
        return val == "아니오"

    # 1. 근육통 관련 진단 (턱 주변 통증이 선택된 경우)
    if any("턱 주변의 통증" in symptom for symptom in selected_symptoms):
        # 국소 근육통 (Local Myalgia)
        if (
            is_yes(state.get("muscle_pressure_2s_value")) and
            is_yes(state.get("muscle_referred_pain_value")) and
            is_no(state.get("muscle_referred_remote_pain_value"))
        ):
            diagnoses.append("국소 근육통 (Local Myalgia)")

        # 방사성 근막통 (Myofascial Pain with Referral)
        elif (
            is_yes(state.get("muscle_pressure_2s_value")) and
            is_yes(state.get("muscle_referred_pain_value")) and
            is_yes(state.get("muscle_referred_remote_pain_value"))
        ):
            diagnoses.append("방사성 근막통 (Myofascial Pain with Referral)")

        # 근육통 (Myalgia)
        elif (
            is_no(state.get("muscle_pressure_2s_value")) or
            (is_yes(state.get("muscle_pressure_2s_value")) and is_no(state.get("muscle_referred_pain_value")))
        ):
            diagnoses.append("근육통 (Myalgia)")

        # 관절통 (Arthralgia)
        if is_yes(state.get("tmj_press_pain_value")):
            diagnoses.append("관절통 (Arthralgia)")

    # 2. 턱관절 소리/잠김 관련 진단
    if any("턱관절 소리" in symptom for symptom in selected_symptoms):
        # 퇴행성 관절 질환
        if is_yes(state.get("crepitus_confirmed_value")):
            diagnoses.append("퇴행성 관절 질환 (Degenerative Joint Disease)")

        # 비정복성 관절원판 변위, 개구 제한 없음
        if is_yes(state.get("mao_fits_3fingers_value")):
            diagnoses.append("비정복성 관절원판 변위, 개구 제한 없음 (Disc Displacement without Reduction)")

        # 비정복성 관절원판 변위, 개구 제한 동반
        elif (
            is_no(state.get("mao_fits_3fingers_value")) or
            is_no(state.get("jaw_unlock_possible_value"))
        ):
            diagnoses.append("비정복성 관절원판 변위, 개구 제한 동반 (Disc Displacement without Reduction with Limited opening)")

        # 정복성 관절원판 변위, 간헐적 개구 장애 동반
        if (
            is_yes(state.get("jaw_locked_now_value")) and
            is_yes(state.get("jaw_unlock_possible_value"))
        ):
            diagnoses.append("정복성 관절원판 변위, 간헐적 개구 장애 동반 (Disc Displacement with reduction, with intermittent locking)")

        # 정복성 관절원판 변위 (딸깍 소리 있을 경우)
        elif state.get("tmj_sound_value") and "딸깍" in state.get("tmj_sound_value"):
            diagnoses.append("정복성 관절원판 변위 (Disc Displacement with Reduction)")

    # 3. 두통 관련 진단
    if any("두통" in symptom for symptom in selected_symptoms) or state.get("has_headache_now") == "예":
        # TMD에 기인한 두통
        if (
            state.get("headache_with_jaw_value") == "예" and
            all(is_yes(state.get(k)) for k in [
                "headache_temples_value",
                "headache_reproduce_by_pressure_value", 
                "headache_not_elsewhere_value",
                "headache_with_jaw_value"
            ])
        ) or (
            state.get("headache_with_jaw_value") == "아니오" and
            is_yes(state.get("headache_temples_value")) and
            is_yes(state.get("headache_reproduce_by_pressure_value"))
        ):
            diagnoses.append("TMD에 기인한 두통 (Headache attributed to TMD)")

    return diagnoses

# ===== PDF 생성 함수 (app.py에서 가져옴) =====
def generate_filled_pdf():
    """수집된 환자 데이터를 템플릿 PDF에 채워넣어 완성된 PDF 생성"""
    template_path = "template5.pdf"
    
    # 템플릿 파일 확인
    if not os.path.exists(template_path):
        st.error(f"⚠️ PDF 템플릿 파일({template_path})을 찾을 수 없습니다.")
        return None
    
    doc = fitz.open(template_path)

    # patient_data를 session_state 형식으로 변환
    # (기존 코드와의 호환성을 위해)
    data = st.session_state.patient_data.copy()
    
    # neck_shoulder_symptoms 변환 (dict일 때만)
    neck_val = data.get("neck_shoulder_symptoms", {})
    if isinstance(neck_val, dict):
        neck_list = [k for k, v in neck_val.items() if v]
        data["neck_shoulder_symptoms"] = ", ".join(neck_list) if neck_list else "없음"

    # additional_symptoms 변환 (dict일 때만)
    add_val = data.get("additional_symptoms", {})
    if isinstance(add_val, dict):
        add_list = [k for k, v in add_val.items() if v]
        data["additional_symptoms"] = ", ".join(add_list) if add_list else "없음"

    # 두통 관련 리스트를 문자열로 변환
    for k in ["headache_areas", "headache_triggers", "headache_reliefs", "headache_frequency"]:
        v = data.get(k, [])
        if isinstance(v, list):
            data[k] = ", ".join(v)

    # 귀 관련 선택도 문자열로 변환
    v = data.get("selected_ear_symptoms", [])
    if isinstance(v, list):
        data["selected_ear_symptoms"] = ", ".join(v)
    
    # 선택된 증상 리스트를 문자열로 변환
    v = data.get("selected_symptoms", [])
    if isinstance(v, list):
        data["selected_symptoms"] = ", ".join(v)
    
    # 습관 리스트를 문자열로 변환
    v = data.get("selected_habits", [])
    if isinstance(v, list):
        data["selected_habits"] = ", ".join(v)

    # PDF에 채워넣을 키 목록
    keys = [
        "name", "birthdate", "gender", "email", "address", "phone",
        "occupation", "visit_reason", "chief_complaint", "chief_complaint_other",
        "onset", "jaw_aggravation", "pain_quality", "pain_quality_other",
        "muscle_movement_pain_value", "muscle_pressure_2s_value",
        "muscle_referred_pain_value", "muscle_referred_remote_pain_value",
        "tmj_movement_pain_value", "tmj_press_pain_value", "headache_temples_value",
        "headache_reproduce_by_pressure_value", "headache_with_jaw_value", "headache_not_elsewhere_value",
        "tmj_sound_value", "tmj_click_context", "crepitus_confirmed_value", "jaw_locked_now_value",
        "jaw_unlock_possible_value", "jaw_locked_past_value", "mao_fits_3fingers_value",
        "frequency_choice", "pain_level", "selected_times",
        "has_headache_now", "headache_areas", "headache_severity", "headache_frequency",
        "headache_triggers", "headache_reliefs", "habit_summary", "selected_habits",
        "habit_none", "habit_bruxism_night", "habit_clenching_day", "habit_clenching_night",
        "active_opening", "active_pain", "passive_opening", "passive_pain",
        "deviation", "deviation2", "deflection", "protrusion", "protrusion_pain",
        "latero_right", "latero_right_pain", "latero_left", "latero_left_pain",
        "occlusion", "occlusion_shift",
        "tmj_noise_right_open", "tmj_noise_left_open", "tmj_noise_right_close", "tmj_noise_left_close",
        "palpation_temporalis", "palpation_medial_pterygoid", "palpation_lateral_pterygoid", "pain_mapping",
        "selected_ear_symptoms", "neck_shoulder_symptoms", "additional_symptoms", "neck_trauma_radio",
        "stress_radio", "stress_detail", "ortho_exp", "ortho_detail", "prosth_exp", "prosth_detail",
        "other_dental", "tmd_treatment_history", "tmd_treatment_detail", "tmd_treatment_response",
        "tmd_current_medications", "past_history", "current_medications", "bite_right", "bite_left",
        "loading_test", "resistance_test", "attrition", "impact_daily", "impact_work", "impact_quality_of_life",
        "sleep_quality", "sleep_tmd_relation", "diagnosis_result", "selected_symptoms",
        "time_morning", "time_afternoon", "time_evening"
    ]

    # 값 준비
    values = {k: str(data.get(k, "")) for k in keys}
    values = {k: ("" if v == "선택 안 함" else v) for k, v in values.items()}
    
    # Boolean 값 변환
    for k, v in values.items():
        if v == "True":
            values[k] = "예"
        elif v == "False":
            values[k] = "아니오"

    # 긴 텍스트 줄바꿈 처리
    for long_key in ["selected_habits", "past_history", "current_medications", "stress_detail", 
                     "ortho_detail", "prosth_detail", "tmd_treatment_detail"]:
        if long_key in values and values[long_key]:
            values[long_key] = "\n".join(textwrap.wrap(values[long_key], width=70))
    
    # 폰트 파일 확인
    if not os.path.exists(FONT_FILE):
        st.warning(f"⚠️ 폰트 파일({FONT_FILE})을 찾을 수 없습니다. 기본 폰트를 사용합니다.")
        font_available = False
    else:
        font_available = True
    
    # PDF에 값 채워넣기
    for page in doc:
        placeholders_to_insert = {}
        for key, val in values.items():
            placeholder = f"{{{key}}}"
            rects = page.search_for(placeholder)
            if rects:
                placeholders_to_insert[key] = {'value': val, 'rects': rects}
                for rect in rects:
                    page.add_redact_annot(rect)

        page.apply_redactions()

        for key, data_item in placeholders_to_insert.items():
            val = data_item['value']
            rects = data_item['rects']
            for rect in rects:
                x, y = rect.tl
                for i, line in enumerate(val.split("\n")):
                    if font_available:
                        page.insert_text((x, y + 8 + i*12), line, fontname="nan", 
                                       fontfile=FONT_FILE, fontsize=10)
                    else:
                        page.insert_text((x, y + 8 + i*12), line, fontsize=10)

    # 업로드된 이미지를 PDF에 추가
    uploaded_images = st.session_state.get("uploaded_images", [])
    if uploaded_images:
        for i, uploaded_image in enumerate(uploaded_images):
            # 새 페이지를 A4 사이즈로 추가
            page = doc.new_page(width=fitz.paper_size("a4")[0], height=fitz.paper_size("a4")[1])
            
            # 페이지 상단에 제목 추가
            title_rect = fitz.Rect(50, 50, page.rect.width - 50, 80)
            if font_available:
                page.insert_textbox(title_rect, f"첨부된 증빙 자료 {i+1}", 
                                  fontsize=14, fontname="nan", fontfile=FONT_FILE, 
                                  align=fitz.TEXT_ALIGN_CENTER)
            else:
                page.insert_textbox(title_rect, f"첨부된 증빙 자료 {i+1}", 
                                  fontsize=14, align=fitz.TEXT_ALIGN_CENTER)

            # 이미지 데이터를 바이트로 읽기
            img_bytes = uploaded_image.getvalue()

            # 이미지를 삽입할 영역 계산 (여백 고려)
            margin = 50
            image_area = fitz.Rect(margin, 100, page.rect.width - margin, page.rect.height - margin)
            
            # 페이지에 이미지 삽입 (가로/세로 비율 유지하며 영역에 맞게)
            page.insert_image(image_area, stream=img_bytes, keep_proportion=True)

    pdf_buffer = BytesIO()
    doc.save(pdf_buffer)
    doc.close()
    pdf_buffer.seek(0)
    return pdf_buffer

# ===== 시스템 프롬프트 (TMD_VARIABLES.md 기반) =====
SYSTEM_PROMPT = """당신은 턱관절 질환(TMD) 전문 의료 상담 AI입니다. 
환자와 친절하고 전문적인 대화를 통해 DC/TMD 진단 기준에 따른 정보를 체계적으로 수집해야 합니다.

**수집해야 할 정보 (단계별):**

## 1단계: 기본 정보 (필수 ⭐)
- name: 이름
- birthdate: 생년월일 (YYYY-MM-DD 형식)
- gender: 성별 ("남성", "여성", "기타")
- email: 이메일
- phone: 연락처
- address: 주소 (선택)
- occupation: 직업 (선택)
- visit_reason: 내원 목적 (선택)

## 2단계: 주 호소 (필수 ⭐)
- selected_symptoms: 현재 증상 리스트 (예: ["턱 주변의 통증(턱 근육, 관자놀이, 귀 앞쪽)", "턱관절 소리/잠김", "턱 움직임 관련 두통"])
- chief_complaint_other: 기타 증상 상세 설명 (조건부)
- onset: 증상 발생 시기 ("일주일 이내", "1개월 이내", "6개월 이내", "1년 이내", "1년 이상 전")

## 3단계: 통증 양상 (필수 ⭐)
- jaw_aggravation: 턱 움직임/기능으로 통증 악화 여부 ("예", "아니오")
- pain_quality: 통증 표현 ("둔함", "날카로움", "욱신거림", "간헐적")

## 4단계: 통증 분류 및 검사 (필수 ⭐)
- pain_types_value: 통증 유형 ("넓은 부위의 통증", "근육 통증", "턱관절 통증", "두통")

### 근육/넓은 부위 통증인 경우:
- muscle_movement_pain_value: 입 벌릴 때/턱 움직일 때 통증 ("예", "아니오")
- muscle_pressure_2s_value: 근육 2초 압박 시 통증 ("예", "아니오")
- muscle_referred_pain_value: 근육 5초 압박 시 통증 전이 ("예", "아니오")
- muscle_referred_remote_pain_value: 통증이 다른 부위(눈, 귀 등)로 전이 ("예", "아니오")

### 턱관절 통증인 경우:
- tmj_movement_pain_value: 입 벌릴 때/움직일 때 통증 ("예", "아니오")
- tmj_press_pain_value: 턱관절 부위 압박 시 기존 통증 재현 ("예", "아니오")

### 두통인 경우:
- headache_temples_value: 관자놀이 부위 두통 ("예", "아니오")
- headache_reproduce_by_pressure_value: 관자놀이 근육 압박 시 두통 재현 ("예", "아니오")
- headache_with_jaw_value: 턱 움직임 시 두통 악화 ("예", "아니오")
- headache_not_elsewhere_value: 다른 의학적 진단으로 설명 안 됨 ("예", "아니오")

## 5단계: 턱관절 소리 및 잠김 (필수 ⭐)
- tmj_sound_value: 턱에서 나는 소리 ("딸깍소리", "사각사각소리(크레피투스)", "없음")
- tmj_click_context: 딸깍소리 발생 상황 리스트 (조건부)
- crepitus_confirmed_value: 사각사각소리 확실한지 ("예", "아니오", 조건부)
- jaw_locked_now_value: 현재 턱 잠김 증상 ("예", "아니오", 조건부)
- jaw_unlock_possible_value: 조작으로 풀림 여부 ("예", "아니오", 조건부)
- jaw_locked_past_value: 과거 턱 잠김 경험 ("예", "아니오", 조건부)
- mao_fits_3fingers_value: 최대 개구 시 손가락 3개 들어감 ("예", "아니오", 조건부)

## 6단계: 빈도 및 시기 (필수 ⭐)
- frequency_choice: 증상 발생 빈도 ("주 1~2회", "주 3~4회", "주 5~6회", "매일")
- pain_level: 현재 통증 정도 (0-10)
- time_morning: 오전 시간대 발생 (true/false)
- time_afternoon: 오후 시간대 발생 (true/false)
- time_evening: 저녁 시간대 발생 (true/false)
- has_headache_now: 두통 여부 ("예", "아니오")

### 두통이 있는 경우:
- headache_areas: 두통 부위 리스트 (["이마", "측두부(관자놀이)", "뒤통수", "정수리"])
- headache_severity: 두통 강도 (0-10)
- headache_frequency: 두통 빈도
- headache_triggers: 두통 유발/악화 요인 리스트
- headache_reliefs: 두통 완화 요인 리스트

## 7단계: 습관 (필수 ⭐)
- habit_none: 해당 습관 없음 (true/false)
- habit_bruxism_night: 이갈이 - 밤 (true/false)
- habit_clenching_day: 이 악물기 - 낮 (true/false)
- habit_clenching_night: 이 악물기 - 밤 (true/false)
- selected_habits: 추가 습관들 리스트 (선택)

## 8~11단계: 의료진 측정 항목 (선택)
이 부분은 환자가 모를 수 있으므로 "의료진이 측정합니다" 또는 "나중에 측정 예정"이라고 안내

## 12단계: 귀 관련 증상 (필수 ⭐)
- selected_ear_symptoms: 귀 관련 증상 리스트 (["이명 (귀울림)", "귀가 먹먹한 느낌", "귀 통증", "청력 저하", "없음"])

## 13단계: 경추/목/어깨 증상 (필수 ⭐)
- neck_shoulder_symptoms: 경추/목/어깨 증상 ("목 통증", "어깨 통증", "뻣뻣함(강직감)", "없음")
- additional_symptoms: 추가 증상 (선택)
- neck_trauma_radio: 목 외상 이력 ("예", "아니오")

## 14단계: 정서적 스트레스 (필수 ⭐)
- stress_radio: 스트레스/불안/우울감 느낌 ("예", "아니오")
- stress_detail: 스트레스 상세 설명 (선택)

## 15단계: 과거 치과적 이력 (필수 ⭐)
- ortho_exp: 교정치료 경험 ("예", "아니오")
- ortho_detail: 교정치료 상세 (조건부)
- prosth_exp: 보철치료 경험 ("예", "아니오")
- prosth_detail: 보철치료 상세 (조건부)
- tmd_treatment_history: 턱관절 질환 치료 경험 ("예", "아니오")
- tmd_treatment_detail: 턱관절 치료 내용 (조건부)

## 16단계: 과거 의과적 이력 (선택)
- past_history: 과거 질환/입원 등 의학적 이력
- current_medications: 현재 복용 중인 약

## 18단계: 기능 평가 (필수 ⭐)
- impact_daily: 일상생활 영향 ("전혀 불편하지 않음", "약간 불편함", "자주 불편함", "매우 불편함")
- impact_work: 직장/학업 영향
- impact_quality_of_life: 삶의 질 영향
- sleep_quality: 최근 2주간 수면의 질 ("좋음", "보통", "나쁨", "매우 나쁨")
- sleep_tmd_relation: 수면↔턱관절 증상 연관성

**대화 규칙:**
1. 한 번에 1개의 관련된 질문만 하세요
2. 환자의 답변에 공감하고 이해를 표현하세요
3. 의학 용어보다는 쉬운 말로 설명하세요
4. 조건부 질문: 이전 답변에 따라 추가 질문을 하세요
   - 예: "두통이 있으시다면..." → 두통 위치, 강도 등 추가 질문
   - 예: "턱에서 소리가 난다면..." → 소리 종류, 발생 상황 등 추가 질문
5. 리스트 형태 답변은 여러 개 선택 가능함을 알려주세요
6. 0-10 척도 질문은 명확히 설명하세요 (0: 없음, 10: 극심함)
7. 충분한 정보를 수집했다고 판단되면 "정보 수집이 완료되었습니다"라고 명확히 말하고 is_complete를 true로 설정하세요
8. 필수 항목(⭐ 표시)을 우선적으로 수집하되, 자연스러운 대화 흐름을 유지하세요

**중요: 응답은 반드시 다음 JSON 형식으로만 작성하세요:**
```json
{
  "message": "환자에게 보낼 메시지 (이모지 사용 가능, 친근하고 공감하는 톤)",
  "collected_data": {
    "변수명": "값",
    "리스트_변수명": ["값1", "값2"]
  },
  "progress": "수집 진행 상황 (예: 기본정보/주호소/통증양상/빈도/습관/생활영향 등)",
  "next_question": "다음에 물어볼 주제",
  "is_complete": false
}
```

**반드시 지켜야 할 사항:**
- JSON 외의 다른 텍스트는 절대 포함하지 마세요
- 변수명은 위에 명시된 정확한 이름을 사용하세요
- 리스트 형태의 답변은 배열로 저장하세요
- "예"/"아니오" 답변은 정확히 그 문자열로 저장하세요
- 날짜는 YYYY-MM-DD 형식으로 저장하세요
- 숫자는 숫자 타입으로 저장하세요 (문자열 X)
"""

def validate_api_key(api_key):
    """API 키 유효성 검증"""
    try:
        client = Anthropic(api_key=api_key)
        # 간단한 테스트 호출
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}]
        )
        return True, client
    except Exception as e:
        return False, str(e)

def call_claude(user_message):
    """Claude API를 호출하여 응답 받기"""
    try:
        if not st.session_state.anthropic_client:
            return "⚠️ API 클라이언트가 초기화되지 않았습니다.", False
        
        # 대화 히스토리 구성
        conversation_history = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            elif msg["role"] == "assistant":
                # assistant 메시지는 실제 표시된 내용만 포함
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg.get("display_content", msg["content"])
                })
        
        # 새 메시지 추가
        conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Claude API 호출
        response = st.session_state.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=conversation_history
        )
        
        assistant_message = response.content[0].text
        
        # JSON 파싱 시도
        try:
            # JSON 코드 블록 제거 (```json ... ``` 형식)
            if "```json" in assistant_message:
                assistant_message = assistant_message.split("```json")[1].split("```")[0].strip()
            elif "```" in assistant_message:
                assistant_message = assistant_message.split("```")[1].split("```")[0].strip()
            
            # JSON 응답 파싱
            parsed_response = json.loads(assistant_message)
            message = parsed_response.get("message", assistant_message)
            collected_data = parsed_response.get("collected_data", {})
            is_complete = parsed_response.get("is_complete", False)
            progress = parsed_response.get("progress", "")
            
            # 수집된 데이터 저장
            if collected_data:
                st.session_state.patient_data.update(collected_data)
            
            # 완료 여부 업데이트
            if is_complete:
                st.session_state.conversation_complete = True
            
            # 실제 표시할 메시지만 반환
            return message, True, progress
            
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 원본 메시지 반환
            st.error(f"JSON 파싱 오류: {str(e)}")
            return assistant_message, False, ""
            
    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}", False, ""

def generate_diagnosis_report(patient_data):
    """환자 데이터를 바탕으로 상세 진단 보고서 생성"""
    
    # 진단 결과 계산
    diagnoses = compute_diagnoses_for_all_symptoms(patient_data)
    
    # diagnosis_result를 patient_data에 저장
    if diagnoses:
        patient_data["diagnosis_result"] = ", ".join(diagnoses)
    else:
        patient_data["diagnosis_result"] = "진단 없음"
    
    dc_tmd_explanations = {
        "근육통 (Myalgia)": "턱 주변 근육에서 발생하는 통증으로, 움직임이나 압박 시 통증이 심해지는 증상입니다.",
        "국소 근육통 (Local Myalgia)": "통증이 특정 근육 부위에만 국한되어 있고, 다른 부위로 퍼지지 않는 증상입니다.",
        "방사성 근막통 (Myofascial Pain with Referral)": "특정 근육을 눌렀을 때 통증이 다른 부위로 방사되어 퍼지는 증상입니다.",
        "관절통 (Arthralgia)": "턱관절 자체에 발생하는 통증으로, 움직이거나 누를 때 통증이 유발되는 상태입니다.",
        "퇴행성 관절 질환 (Degenerative Joint Disease)": "턱관절의 연골이나 뼈가 마모되거나 손상되어 통증과 기능 제한이 동반되는 상태입니다.",
        "비정복성 관절원판 변위, 개구 제한 없음 (Disc Displacement without Reduction)": "턱관절 디스크가 비정상 위치에 있으며, 입을 벌려도 제자리로 돌아오지 않는 상태입니다.",
        "비정복성 관절원판 변위, 개구 제한 동반 (Disc Displacement without Reduction with Limited opening)": "디스크가 제자리로 돌아오지 않으며, 입 벌리기가 제한되는 상태입니다.",
        "정복성 관절원판 변위, 간헐적 개구 장애 동반 (Disc Displacement with reduction, with intermittent locking)": "디스크가 움직일 때 딸깍소리가 나며, 일시적인 입 벌리기 장애가 간헐적으로 나타나는 상태입니다.",
        "정복성 관절원판 변위 (Disc Displacement with Reduction)": "입을 벌릴 때 디스크가 제자리로 돌아오며 딸깍소리가 나는 상태이며, 기능 제한은 없는 경우입니다.",
        "TMD에 기인한 두통 (Headache attributed to TMD)": "턱관절 또는 턱 주변 근육 문제로 인해 발생하는 두통으로, 턱을 움직이거나 근육을 누르면 증상이 악화되는 경우입니다."
    }
    
    report = "# 🔍 턱관절 질환 예비 진단 결과\n\n"
    report += "---\n\n"
    
    if not diagnoses:
        report += "## ✅ 진단 결과\n\n"
        report += "DC/TMD 기준상 명확한 진단 근거는 확인되지 않았습니다.\n\n"
        report += "다른 질환 가능성에 대한 조사가 필요합니다.\n\n"
    else:
        report += "## ⚠️ 진단 결과\n\n"
        if len(diagnoses) == 1:
            report += f"**{diagnoses[0]}** 이(가) 의심됩니다.\n\n"
        else:
            report += f"다음 진단들이 의심됩니다:\n"
            for d in diagnoses:
                report += f"- **{d}**\n"
            report += "\n"
        
        report += "---\n\n"
        report += "## 📋 진단별 상세 설명\n\n"
        for diagnosis in diagnoses:
            report += f"### 🔹 {diagnosis}\n\n"
            report += f"{dc_tmd_explanations.get(diagnosis, '설명 없음')}\n\n"
            report += "---\n\n"
    
    report += "## 💡 권장 사항\n\n"
    report += "※ 본 결과는 예비 진단이며, 정확한 진단과 치료를 위해서는 반드시 턱관절 전문의 상담을 받으시기 바랍니다.\n\n"
    report += "※ 증상이 지속되거나 악화될 경우 즉시 의료기관을 방문하세요.\n"
    
    return report, diagnoses

# ========== 사이드바: API 키 입력 ==========
with st.sidebar:
    st.header("🔐 API 설정")
    
    # 환경변수에서 API 키 확인
    env_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # secrets에서 API 키 확인
    try:
        secrets_api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except:
        secrets_api_key = None
    
    # 사용 가능한 API 키 선택
    available_api_key = env_api_key or secrets_api_key
    
    if available_api_key and not st.session_state.api_key_validated:
        with st.spinner("API 키 확인 중..."):
            is_valid, result = validate_api_key(available_api_key)
            if is_valid:
                st.session_state.api_key_validated = True
                st.session_state.anthropic_client = result
                st.success("✅ API 키가 인증되었습니다!")
            else:
                st.warning("⚠️ 저장된 API 키가 유효하지 않습니다.")
    
    # API 키 수동 입력
    if not st.session_state.api_key_validated:
        st.info("💡 Anthropic API 키를 입력하세요")
        st.markdown("""
        API 키가 없으시면:
        1. [Anthropic Console](https://console.anthropic.com) 접속
        2. API Keys 메뉴에서 키 생성
        3. 아래에 입력하세요
        """)
        
        api_key_input = st.text_input(
            "API 키 입력",
            type="password",
            placeholder="sk-ant-api03-...",
            help="API 키는 'sk-ant-'로 시작합니다"
        )
        
        if st.button("🔑 API 키 인증", use_container_width=True):
            if api_key_input:
                with st.spinner("API 키 검증 중..."):
                    is_valid, result = validate_api_key(api_key_input)
                    if is_valid:
                        st.session_state.api_key_validated = True
                        st.session_state.anthropic_client = result
                        st.success("✅ API 키가 인증되었습니다!")
                        st.rerun()
                    else:
                        st.error(f"❌ API 키가 유효하지 않습니다.\n\n오류: {result}")
            else:
                st.warning("⚠️ API 키를 입력해주세요.")
    
    else:
        st.success("✅ API 연결됨")
        if st.button("🔄 API 키 재설정"):
            st.session_state.api_key_validated = False
            st.session_state.anthropic_client = None
            st.rerun()
    
    st.markdown("---")
    
    # 수집된 정보 표시
    if st.session_state.api_key_validated:
        st.header("📋 수집된 정보")
        
        # 수집 진행률 계산
        required_fields = [
            "name", "birthdate", "gender", "email", "phone",
            "selected_symptoms", "onset", "jaw_aggravation", "pain_quality",
            "frequency_choice", "pain_level", "has_headache_now",
            "selected_ear_symptoms", "neck_trauma_radio", "stress_radio",
            "ortho_exp", "prosth_exp", "tmd_treatment_history",
            "impact_daily", "impact_work", "impact_quality_of_life",
            "sleep_quality", "sleep_tmd_relation"
        ]
        
        collected_count = sum(1 for field in required_fields if field in st.session_state.patient_data)
        progress = collected_count / len(required_fields)
        
        st.progress(progress)
        st.caption(f"필수 정보: {collected_count}/{len(required_fields)} 수집됨")
        
        if st.session_state.patient_data:
            with st.expander("수집된 데이터 보기"):
                st.json(st.session_state.patient_data)
        else:
            st.info("아직 수집된 정보가 없습니다.")
        
        st.markdown("---")
        
        if st.button("🔄 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.patient_data = {}
            st.session_state.conversation_complete = False
            st.rerun()

# ========== 메인 화면 ==========
st.title("🦷 턱관절 AI 대화형 문진 시스템")
st.markdown("---")

# API 키가 인증되지 않은 경우
if not st.session_state.api_key_validated:
    st.warning("⚠️ 먼저 왼쪽 사이드바에서 API 키를 설정해주세요.")
    st.info("""
    ### 📌 API 키 설정 방법
    
    **방법 1: 사이드바에서 직접 입력** (가장 쉬움)
    - 왼쪽 사이드바에서 API 키를 입력하고 인증 버튼 클릭
    
    **방법 2: secrets.toml 파일 사용**
    1. `.streamlit` 폴더 생성
    2. `secrets.toml` 파일 생성
    3. 다음 내용 입력:
    ```
    ANTHROPIC_API_KEY = "sk-ant-your-key"
    ```
    """)
    st.stop()

# 대화 시작 메시지
if not st.session_state.messages:
    initial_message = """안녕하세요! 저는 턱관절 질환 상담을 도와드리는 AI 어시스턴트입니다. 😊

DC/TMD 진단 기준에 따라 체계적으로 증상을 확인하고, 예비 진단을 제공해드립니다.

먼저 기본 정보부터 여쭤보겠습니다.
**성함**이 어떻게 되시나요?"""
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": initial_message,
        "display_content": initial_message
    })

# 대화 히스토리 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # display_content가 있으면 그것을 사용, 없으면 content 사용
        display_text = message.get("display_content", message["content"])
        st.markdown(display_text)

# 사용자 입력
if not st.session_state.conversation_complete:
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "display_content": prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Claude 응답 받기
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                response, is_json, progress = call_claude(prompt)
                st.markdown(response)
                
                # 진행 상황 표시
                if progress:
                    st.caption(f"📍 현재 단계: {progress}")
                
                # 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "display_content": response
                })
        
        st.rerun()
else:
    st.success("✅ 정보 수집이 완료되었습니다!")
    
    # 진단 결과 생성 및 표시
    st.markdown("---")
    
    # 진단 결과 표시
    with st.spinner("진단 생성 중..."):
        report, diagnoses = generate_diagnosis_report(st.session_state.patient_data)
        st.markdown(report)
    
    st.markdown("---")
    
    # 증빙자료 첨부 섹션
    st.subheader("📸 증빙자료 첨부 (선택 사항)")
    st.info("X-ray, 파노라마 사진 등 관련 자료가 있다면 PDF 보고서에 함께 첨부할 수 있습니다.")
    
    st.session_state.uploaded_images = st.file_uploader(
        "이미지 파일을 선택하세요 (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="evidence_uploader"
    )
    
    st.markdown("---")
    
    # 버튼 그룹
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # PDF 다운로드 버튼
        if st.button("📥 진단 결과 PDF 다운로드", use_container_width=True):
            with st.spinner("PDF 생성 중..."):
                pdf_buffer = generate_filled_pdf()
                if pdf_buffer:
                    st.download_button(
                        label="💾 PDF 파일 저장",
                        data=pdf_buffer,
                        file_name=f"턱관절_진단_결과_{datetime.date.today()}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF가 생성되었습니다!")
                else:
                    st.error("❌ PDF 생성에 실패했습니다.")
    
    with col2:
        if st.button("🔄 새로운 문진 시작", use_container_width=True):
            st.session_state.messages = []
            st.session_state.patient_data = {}
            st.session_state.conversation_complete = False
            if 'uploaded_images' in st.session_state:
                del st.session_state.uploaded_images
            st.rerun()
    
    with col3:
        # 데이터 내보내기 버튼
        if st.button("📋 데이터 JSON 다운로드", use_container_width=True):
            json_data = json.dumps(st.session_state.patient_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="💾 JSON 파일 저장",
                data=json_data,
                file_name=f"턱관절_데이터_{datetime.date.today()}.json",
                mime="application/json",
                use_container_width=True
            )
    
    # 수집된 전체 데이터 표시
    with st.expander("📝 수집된 전체 데이터 보기"):
        st.json(st.session_state.patient_data)

# 스타일링
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stChatInputContainer {
        padding: 1rem 0;
    }
    .stSidebar {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)
