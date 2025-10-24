"""
Firebase 연결 테스트 스크립트 (Python 직접 실행용)

실행 방법:
    python test_firebase_simple.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from datetime import datetime
import json
import os

def load_secrets_from_toml():
    """secrets.toml 파일을 읽어서 Firebase 설정 추출"""
    secrets_path = ".streamlit/secrets.toml"
    
    if not os.path.exists(secrets_path):
        print(f"❌ {secrets_path} 파일을 찾을 수 없습니다.")
        return None
    
    firebase_config = {}
    current_section = None
    
    with open(secrets_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # [firebase] 섹션 찾기
            if line == '[firebase]':
                current_section = 'firebase'
                continue
            
            # 다른 섹션 시작되면 중단
            if line.startswith('[') and line != '[firebase]':
                current_section = None
                continue
            
            # firebase 섹션의 키-값 파싱
            if current_section == 'firebase' and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                # 줄바꿈 처리
                value = value.replace('\\n', '\n')
                
                firebase_config[key] = value
    
    return firebase_config

def test_firebase_connection():
    """Firebase 연결 테스트"""
    print("=" * 60)
    print("🔧 Firebase 연결 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. secrets.toml 읽기
        print("\n[1/5] secrets.toml 읽기 중...")
        firebase_config = load_secrets_from_toml()
        
        if not firebase_config:
            print("❌ secrets.toml 파일을 읽을 수 없습니다.")
            return False
        
        print(f"✅ secrets.toml 읽기 성공")
        print(f"    프로젝트 ID: {firebase_config.get('project_id')}")
        
        # 2. Firebase 초기화
        print("\n[2/5] Firebase 초기화 중...")
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase 초기화 성공")
        
        # 3. 테스트 데이터 쓰기
        print("\n[3/5] 테스트 데이터 쓰기 중...")
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
        print(f"    테스트 ID: {test_id}")
        
        # 4. 테스트 데이터 읽기
        print("\n[4/5] 테스트 데이터 읽기 중...")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            print("✅ 데이터 읽기 성공")
            print(f"    메시지: {data.get('message')}")
        else:
            print("❌ 데이터를 찾을 수 없음")
            return False
        
        # 5. 테스트 데이터 삭제
        print("\n[5/5] 테스트 데이터 삭제 중...")
        doc_ref.delete()
        print("✅ 데이터 삭제 성공")
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        print("\n📝 다음 단계:")
        print("1. streamlit run app_int2_firebase.py")
        print("2. 브라우저에서 앱이 정상 작동하는지 확인")
        print("3. Firebase Console에서 데이터 확인")
        print("   → https://console.firebase.google.com/")
        print(f"   → Firestore Database → tmd_sessions 컬렉션")
        
        return True
        
    except KeyError as e:
        print(f"\n❌ secrets.toml 설정 오류")
        print(f"    누락된 키: {e}")
        print("\n💡 해결 방법:")
        print("1. .streamlit/secrets.toml 파일 확인")
        print("2. [firebase] 섹션의 모든 키가 있는지 확인")
        print("3. FIREBASE_SETUP_GUIDE.md 참고")
        return False
        
    except FileNotFoundError:
        print(f"\n❌ .streamlit/secrets.toml 파일을 찾을 수 없습니다.")
        print("\n💡 해결 방법:")
        print("1. 프로젝트 루트에 .streamlit 폴더 생성")
        print("2. secrets.toml 파일 생성")
        print("3. secrets.toml.template 참고하여 내용 작성")
        return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {type(e).__name__}")
        print(f"    상세: {str(e)}")
        print("\n💡 해결 방법:")
        print("1. Firebase Console에서 프로젝트 설정 확인")
        print("2. 서비스 계정 키가 올바른지 확인")
        print("3. private_key에 줄바꿈(\\n)이 포함되어 있는지 확인")
        print("4. FIREBASE_SETUP_GUIDE.md의 문제 해결 섹션 참고")
        
        # 상세 에러 출력
        import traceback
        print("\n🔍 상세 에러 메시지:")
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("       Firebase 연결 테스트 도구 (Python 직접 실행)")
    print("=" * 60)
    
    # 필요한 패키지 확인
    print("\n📦 필요한 패키지 확인 중...")
    try:
        import firebase_admin
        print("✅ firebase-admin 설치됨")
    except ImportError:
        print("❌ firebase-admin이 설치되지 않았습니다.")
        print("   실행: pip install firebase-admin")
        exit(1)
    
    print("\n" + "-" * 60)
    
    success = test_firebase_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 테스트 완료 - Firebase 설정이 올바릅니다!")
    else:
        print("❌ 테스트 실패 - 위의 해결 방법을 참고하세요.")
    print("=" * 60 + "\n")
    
    exit(0 if success else 1)
