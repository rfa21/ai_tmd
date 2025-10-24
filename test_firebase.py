"""
Firebase 연결 테스트 스크립트
이 스크립트를 실행하여 Firebase 설정이 올바른지 확인하세요.
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from datetime import datetime

def test_firebase_connection():
    """Firebase 연결 테스트"""
    print("=" * 50)
    print("Firebase 연결 테스트 시작")
    print("=" * 50)
    
    try:
        # secrets.toml 읽기
        print("\n1. secrets.toml 읽기 중...")
        firebase_config = dict(st.secrets["firebase"])
        print("✅ secrets.toml 읽기 성공")
        print(f"   프로젝트 ID: {firebase_config.get('project_id')}")
        
        # Firebase 초기화
        print("\n2. Firebase 초기화 중...")
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase 초기화 성공")
        
        # 테스트 데이터 쓰기
        print("\n3. 테스트 데이터 쓰기 중...")
        test_id = str(uuid.uuid4())
        test_data = {
            'test': True,
            'message': 'Firebase 연결 테스트',
            'timestamp': datetime.now(),
            'test_id': test_id
        }
        doc_ref = db.collection('test_collection').document('test_doc')
        doc_ref.set(test_data)
        print("✅ 데이터 쓰기 성공")
        print(f"   테스트 ID: {test_id}")
        
        # 테스트 데이터 읽기
        print("\n4. 테스트 데이터 읽기 중...")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            print("✅ 데이터 읽기 성공")
            print(f"   읽은 데이터: {data}")
        else:
            print("❌ 데이터를 찾을 수 없음")
            return False
        
        # 테스트 데이터 삭제
        print("\n5. 테스트 데이터 삭제 중...")
        doc_ref.delete()
        print("✅ 데이터 삭제 성공")
        
        print("\n" + "=" * 50)
        print("🎉 모든 테스트 통과!")
        print("=" * 50)
        print("\n다음 단계:")
        print("1. streamlit run app_int2_firebase.py")
        print("2. 브라우저에서 앱이 정상 작동하는지 확인")
        print("3. 대화 입력 후 Firebase Console에서 데이터 확인")
        print("   → https://console.firebase.google.com/")
        print("   → Firestore Database → tmd_sessions 컬렉션")
        
        return True
        
    except KeyError as e:
        print(f"\n❌ secrets.toml 설정 오류")
        print(f"   누락된 키: {e}")
        print("\n해결 방법:")
        print("1. .streamlit/secrets.toml 파일 확인")
        print("2. firebase 섹션의 모든 키가 있는지 확인")
        print("3. FIREBASE_SETUP_GUIDE.md 참고")
        return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {type(e).__name__}")
        print(f"   상세: {str(e)}")
        print("\n해결 방법:")
        print("1. Firebase Console에서 프로젝트 설정 확인")
        print("2. 서비스 계정 키가 올바른지 확인")
        print("3. private_key에 줄바꿈(\\n)이 포함되어 있는지 확인")
        print("4. FIREBASE_SETUP_GUIDE.md의 문제 해결 섹션 참고")
        return False

if __name__ == "__main__":
    print("\n🔧 Firebase 연결 테스트 도구")
    print("이 스크립트는 Firebase 설정이 올바른지 확인합니다.\n")
    
    try:
        test_firebase_connection()
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        print("\nstreamlit 환경에서 실행해야 합니다:")
        print("streamlit run test_firebase.py")
