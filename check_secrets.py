"""
secrets.toml 검증 도구
Firebase 설정이 올바른지 확인합니다.

실행 방법:
    python check_secrets.py
"""

import os

def check_secrets_toml():
    """secrets.toml 파일 검증"""
    print("=" * 60)
    print("🔍 secrets.toml 파일 검증")
    print("=" * 60)
    
    secrets_path = ".streamlit/secrets.toml"
    
    # 파일 존재 확인
    print(f"\n📁 파일 확인: {secrets_path}")
    if not os.path.exists(secrets_path):
        print(f"❌ 파일이 존재하지 않습니다!")
        print("\n💡 해결 방법:")
        print("1. mkdir -p .streamlit")
        print("2. secrets.toml.template을 .streamlit/secrets.toml로 복사")
        print("3. 내용 수정")
        return False
    
    print("✅ 파일이 존재합니다")
    
    # 파일 읽기
    print("\n📖 파일 읽기 중...")
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 파일을 읽을 수 없습니다: {e}")
        return False
    
    print(f"✅ 파일 크기: {len(content)} bytes")
    
    # [firebase] 섹션 확인
    print("\n🔍 [firebase] 섹션 확인...")
    if '[firebase]' not in content:
        print("❌ [firebase] 섹션이 없습니다!")
        print("\n💡 secrets.toml에 다음을 추가하세요:")
        print("[firebase]")
        print('type = "service_account"')
        print('project_id = "your-project-id"')
        print("...")
        return False
    
    print("✅ [firebase] 섹션이 있습니다")
    
    # 필수 필드 확인
    print("\n📋 필수 필드 확인...")
    required_fields = [
        'type',
        'project_id',
        'private_key_id',
        'private_key',
        'client_email',
        'client_id',
        'auth_uri',
        'token_uri',
        'auth_provider_x509_cert_url',
        'client_x509_cert_url'
    ]
    
    firebase_section = content.split('[firebase]')[1].split('[')[0] if '[firebase]' in content else ''
    
    missing_fields = []
    found_fields = []
    
    for field in required_fields:
        if f'{field} =' in firebase_section or f'{field}=' in firebase_section:
            found_fields.append(field)
            print(f"  ✅ {field}")
        else:
            missing_fields.append(field)
            print(f"  ❌ {field} (누락)")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print(f"📊 검증 결과: {len(found_fields)}/{len(required_fields)} 필드 발견")
    print("=" * 60)
    
    if missing_fields:
        print(f"\n❌ 누락된 필드: {', '.join(missing_fields)}")
        print("\n💡 해결 방법:")
        print("1. Firebase Console → 프로젝트 설정 → 서비스 계정")
        print("2. '새 비공개 키 생성' 클릭 → JSON 다운로드")
        print("3. JSON 파일의 내용을 secrets.toml의 [firebase] 섹션에 복사")
        print("\n예시:")
        print('[firebase]')
        print('type = "service_account"')
        print('project_id = "your-project-id"')
        print('private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"')
        print('...')
        return False
    
    # private_key 형식 확인
    print("\n🔐 private_key 형식 확인...")
    if 'private_key = "-----BEGIN PRIVATE KEY-----' in firebase_section:
        print("✅ private_key 시작 부분이 올바릅니다")
        if '-----END PRIVATE KEY-----' in firebase_section:
            print("✅ private_key 끝 부분이 올바릅니다")
            if '\\n' in firebase_section:
                print("✅ 줄바꿈(\\n)이 포함되어 있습니다")
            else:
                print("⚠️  줄바꿈(\\n)이 없을 수 있습니다")
                print("    private_key에는 \\n이 포함되어야 합니다:")
                print('    private_key = "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n"')
        else:
            print("❌ private_key 끝 부분이 없습니다")
    else:
        print("❌ private_key 형식이 올바르지 않습니다")
    
    # 쉼표 확인
    print("\n🔍 잘못된 형식 확인...")
    issues = []
    
    lines = firebase_section.split('\n')
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # 쉼표로 끝나는지 확인
        if '=' in line and line.rstrip().endswith(','):
            issues.append(f"  ⚠️  라인 {i}: 끝에 쉼표(,)가 있습니다 → 제거하세요")
            print(f"  ⚠️  라인 {i}: '{line[:50]}...' ← 끝에 쉼표 제거 필요")
    
    if issues:
        print(f"\n⚠️  {len(issues)}개의 형식 문제 발견:")
        for issue in issues:
            print(issue)
        print("\n💡 TOML 형식에서는 각 줄 끝에 쉼표를 넣지 않습니다!")
    else:
        print("✅ 형식 문제가 없습니다")
    
    # 최종 결과
    print("\n" + "=" * 60)
    if not missing_fields and not issues:
        print("✅ secrets.toml 파일이 올바릅니다!")
        print("\n다음 단계:")
        print("  python test_firebase_simple.py")
        print("또는")
        print("  streamlit run test_firebase.py")
    else:
        print("❌ secrets.toml 파일에 문제가 있습니다")
        print("\n위의 해결 방법을 참고하여 수정하세요.")
    print("=" * 60)
    
    return not missing_fields and not issues

if __name__ == "__main__":
    success = check_secrets_toml()
    exit(0 if success else 1)
