"""
마비노기 모바일 룬 챗봇 서버
카카오 i 오픈빌더 스킬 서버용

실행: python app.py
포트: 5000 (환경 변수 PORT로 변경 가능)

사용법: /룬 낙화
"""

from flask import Flask, request, jsonify
import os
from rune_data import search_rune, format_rune_info, RUNE_DATA

app = Flask(__name__)


def handle_rune_command(user_text: str) -> str:
    """
    /룬 <룬이름> 명령어 처리
    예: /룬 낙화, /룬 불길, /룬 여명
    """
    # "/룬" 제거하고 룬 이름 추출
    text = user_text.strip()
    
    if text.startswith("/룬"):
        rune_name = text[2:].strip()
    else:
        rune_name = text.strip()
    
    if not rune_name:
        return (
            "🗡️ 룬 정보 검색\n\n"
            "사용법: /룬 <룬 이름>\n\n"
            "예시:\n"
            "• /룬 낙화\n"
            "• /룬 불길\n"
            "• /룬 여명\n"
            "• /룬 폭군\n\n"
            "💡 부분 이름도 검색 가능합니다!"
        )
    
    name, data = search_rune(rune_name)
    
    if name and isinstance(data, dict):
        # 단일 결과
        return format_rune_info(name, data)
    
    elif data and isinstance(data, list):
        # 여러 결과
        result_names = [r[0] for r in data[:10]]  # 최대 10개
        msg = f"🔍 '{rune_name}' 검색 결과 {len(data)}개\n\n"
        msg += "\n".join(f"• {n}" for n in result_names)
        if len(data) > 10:
            msg += f"\n... 외 {len(data) - 10}개"
        msg += "\n\n💡 정확한 이름으로 다시 검색해보세요!"
        return msg
    
    else:
        # 결과 없음
        return (
            f"❌ '{rune_name}' 룬을 찾을 수 없습니다.\n\n"
            "💡 다음을 확인해보세요:\n"
            "• 룬 이름 철자를 확인해주세요\n"
            "• /룬 목록 으로 전체 룬을 확인하세요"
        )


def handle_list_command(user_text: str) -> str:
    """
    /룬 목록 또는 /룬 목록 <분류> 명령어 처리
    분류: 무기, 방어구, 엠블럼, 장신구
    """
    text = user_text.strip()
    
    # "/룬 목록" 이후 분류어 추출
    if "목록" in text:
        after = text[text.find("목록") + 2:].strip()
    else:
        after = ""
    
    # 분류별 필터링
    분류_필터 = None
    분류_키워드 = {
        "무기": "무기",
        "방어구": "방어구",
        "엠블럼": "엠블럼",
        "장신구": "장신구",
    }
    
    for keyword, 분류 in 분류_키워드.items():
        if keyword in after:
            분류_필터 = 분류
            break
    
    # 등급별 필터링
    등급_필터 = None
    if "신화" in after:
        등급_필터 = "신화"
    elif "전설" in after:
        등급_필터 = "전설"
    elif "에픽" in after:
        등급_필터 = "에픽"
    
    # 필터 적용
    filtered = {}
    for name, data in RUNE_DATA.items():
        if 분류_필터 and 분류_필터 not in data.get("분류", ""):
            continue
        if 등급_필터 and 등급_필터 not in data.get("등급", ""):
            continue
        filtered[name] = data
    
    if not filtered:
        return "해당 조건의 룬을 찾을 수 없습니다."
    
    # 분류별로 그룹화
    groups = {}
    for name, data in filtered.items():
        분류 = data.get("분류", "기타")
        # 장신구 세부 분류 통합
        if "장신구" in 분류:
            group_key = 분류
        else:
            group_key = f"{분류} ({data.get('등급', '')})"
        groups.setdefault(group_key, []).append(name)
    
    title_parts = []
    if 분류_필터:
        title_parts.append(분류_필터)
    if 등급_필터:
        title_parts.append(등급_필터)
    
    title = " ".join(title_parts) + " 룬 목록" if title_parts else "전체 룬 목록"
    
    msg = f"📋 {title} ({len(filtered)}개)\n\n"
    
    for group, names in sorted(groups.items()):
        msg += f"【{group}】\n"
        msg += ", ".join(names) + "\n\n"
    
    return msg.strip()


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "마비노기 모바일 룬 챗봇 서버 가동 중"})


@app.route("/webhook", methods=["POST"])
def kakao_webhook():
    """
    카카오 i 오픈빌더 스킬 서버 웹훅 엔드포인트
    """
    try:
        body = request.get_json()
        
        # 카카오 오픈빌더 요청에서 사용자 발화 추출
        user_text = ""
        
        if body:
            # 카카오 i 오픈빌더 형식
            utterance = (
                body.get("userRequest", {})
                    .get("utterance", "")
            )
            if utterance:
                user_text = utterance
            
            # 파라미터에서 룬 이름 직접 받기 (엔티티 설정 시)
            action = body.get("action", {})
            params = action.get("params", {})
            if "rune_name" in params:
                rune_query = params["rune_name"]
                name, data = search_rune(rune_query)
                if name and isinstance(data, dict):
                    response_text = format_rune_info(name, data)
                else:
                    response_text = f"'{rune_query}' 룬을 찾을 수 없습니다."
                return build_kakao_response(response_text)
        
        # 명령어 파싱
        if not user_text:
            return build_kakao_response("메시지를 인식할 수 없습니다.")
        
        # 목록 조회
        if "목록" in user_text:
            response_text = handle_list_command(user_text)
        # 룬 정보 조회
        elif "/룬" in user_text:
            response_text = handle_rune_command(user_text)
        else:
            response_text = (
                "💡 사용 가능한 명령어:\n\n"
                "/룬 <이름> - 룬 정보 검색\n"
                "/룬 목록 - 전체 룬 목록\n"
                "/룬 목록 무기 - 무기 룬 목록\n"
                "/룬 목록 방어구 전설 - 방어구 전설 룬\n"
                "/룬 목록 엠블럼 - 엠블럼 룬 목록"
            )
        
        return build_kakao_response(response_text)
    
    except Exception as e:
        print(f"Error: {e}")
        return build_kakao_response("오류가 발생했습니다. 다시 시도해주세요.")


def build_kakao_response(text: str) -> dict:
    """카카오 i 오픈빌더 응답 형식으로 변환"""
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    })


# =============================================
# 일반 HTTP 테스트용 엔드포인트 (카카오 외)
# =============================================

@app.route("/rune", methods=["GET"])
def get_rune():
    """
    직접 테스트용: GET /rune?name=낙화
    """
    name_query = request.args.get("name", "").strip()
    if not name_query:
        return jsonify({"error": "name 파라미터를 입력해주세요. 예: /rune?name=낙화"})
    
    name, data = search_rune(name_query)
    
    if name and isinstance(data, dict):
        return jsonify({
            "found": True,
            "name": name,
            "data": {k: v for k, v in data.items() if k != "별칭"},
            "formatted": format_rune_info(name, data)
        })
    elif data and isinstance(data, list):
        return jsonify({
            "found": False,
            "multiple": True,
            "results": [r[0] for r in data]
        })
    else:
        return jsonify({"found": False, "message": f"'{name_query}' 룬을 찾을 수 없습니다."})


@app.route("/rune/list", methods=["GET"])
def list_runes():
    """
    직접 테스트용: GET /rune/list?category=무기&grade=전설
    """
    category = request.args.get("category", "").strip()
    grade = request.args.get("grade", "").strip()
    
    filtered = {}
    for name, data in RUNE_DATA.items():
        if category and category not in data.get("분류", ""):
            continue
        if grade and grade not in data.get("등급", ""):
            continue
        filtered[name] = {k: v for k, v in data.items() if k != "별칭"}
    
    return jsonify({
        "count": len(filtered),
        "runes": filtered
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🗡️ 마비노기 모바일 룬 챗봇 서버 시작 (포트: {port})")
    print(f"📊 총 {len(RUNE_DATA)}개 룬 데이터 로드 완료")
    app.run(host="0.0.0.0", port=port, debug=False)
