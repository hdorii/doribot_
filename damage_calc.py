"""
마비노기 모바일 데미지 계산기
공식: 대미지 = roundup(2 * [민댐~맥댐] * rounddown(A*B, 0) * C*D*E*F*G*H*I*J*K*L * 스킬계수, 0)
"""
import math
from dataclasses import dataclass, field
from typing import Optional


# =============================================
# 클래스별 자버프 정의
# =============================================
CLASS_BUFFS = {
    "검술사": {
        "description": "집중 상태 시 치확 +40%, 치피 +30% / 전투숙련 치피 +5% / 날카로운눈 치피 최대 +30%",
        "crit_rate_bonus": 40.0,      # 집중 상태 치확
        "crit_dmg_bonus": 30.0,       # 집중 상태 치피
        "passive_crit_dmg": 5.0,      # 전투숙련: 위협
        "note": "날카로운눈 10스택 시 치피 +30% 추가 (선택)"
    },
    "대검전사": {
        "description": "전투숙련 강타피해 +5% / 보복 체력소모마다 공격력 +5% (무제한중첩)",
        "passive_strong_dmg": 5.0,    # 전투숙련: 패기
        "note": "보복 스택은 수동 입력 필요"
    },
    "석궁사수": {
        "description": "전투숙련 치피 +5% / 드라이빙포스 피해 +30% (최대2스택) / 퀵어택 스킬속도 +5% (최대3스택)",
        "passive_crit_dmg": 5.0,      # 전투숙련: 위협
        "note": "드라이빙포스는 동일스킬 연속사용 시 적용"
    },
    "화염술사": {
        "description": "버닝소울 최종피해 +3%/+6%/+15% (1/2/3단계) / 전투숙련 멀티히트 +5%",
        "passive_multihit_dmg": 5.0,  # 전투숙련: 기교
        "note": "버닝소울 단계는 수동 입력"
    },
    "마법사": {
        "description": "아케인파워 공격력 최대 +9% (조건부) / 전투숙련 멀티히트 +5%",
        "passive_multihit_dmg": 5.0,  # 전투숙련: 기교
        "cond_atk_bonus": 9.0,        # 아케인파워 조건부 공격력
        "note": "아케인파워는 원소속성 공격 시 조건부"
    },
    "악사": {
        "description": "전투숙련 연타피해 +5% / 모데라토 다음스킬 피해 +25% (무드 50 넘나들 때)",
        "passive_multi_dmg": 5.0,     # 전투숙련: 쾌속
        "note": "모데라토는 조건부 순간버프"
    },
    "도적": {
        "description": "전투숙련 연타피해 +5% / 스닉어택 추가타확률 +15% (7초) / 포이즌익스플로전 중독폭발 +5%",
        "passive_multi_dmg": 5.0,     # 전투숙련: 쾌속
        "addl_hit_rate_bonus": 15.0,  # 스닉어택
        "note": "스닉어택: 첫공격/은신진입해제 시 추가타확률 +15%"
    },
}

# 지원 예정 클래스 (자버프 미입력)
PENDING_CLASSES = ["전사", "듀얼블레이드", "궁수", "빙결술사", "전격술사"]

# 룬 파싱용 - 지원하는 룬 목록과 효과
# 형식: 룬이름+등급 → 효과 딕셔너리
# 등급: 1=엘리트, 2=에픽, 3=전설(기본), 4=전설(중간), 5=전설(최고)
RUNE_EFFECTS = {
    # 무기 룬
    "검무": {"공증": [22.0, 22.0, 22.0, 22.0, 24.0], "치확": [10.0, 10.0, 10.0, 10.0, 10.0], "note": "10스택 기준"},
    "검무2": {"공증": 24.0, "치확": 10.0, "note": "10스택 기준"},
    "아득2": {"치확": [5.0, 5.0, 5.0, 20.0, 20.0], "치피": [10.0, 10.0, 10.0, 62.0, 62.0], "피증": [7.0, 7.0, 7.0, 7.0, 7.0],
              "각성치확": 20.0, "각성치피": 62.0, "note": "비각성/각성 분리"},
    "섬세2": {"공증": 10.0, "연피": 6.0, "추확": 4.0, "note": "각성포함 동일"},
    "압도2": {"공증": 10.0, "강피": 6.0, "치확": 4.0, "note": "각성포함 동일"},
    "바빛": {"공증": 27.5, "note": "바스러지는빛 5스택"},
    "일렁2": {"추확": 24.15, "각성추가댐": 30.0, "note": "90초전력810기준/각성시과부하"},
    "황혼2": {"피증": 27.2, "note": "가동률100%"},
    "장신구2": {"최종댐": 3.0225, "note": "2초월 1.5% 두번"},
    "인챈트크레센도": {"피증": 1.0},
    # 방어구 룬
    "불길": {"치확": [18.0, 18.0, 20.0, 20.0, 22.0]},
    "결정": {"추확": [18.0, 18.0, 20.0, 20.0, 22.0]},
    "뇌명": {"강피": [20.0, 20.0, 22.0, 22.0, 24.0]},
    "야수": {"피증": [20.0, 20.0, 22.0, 22.0, 24.0]},
    "공포": {"치피": [18.0, 18.0, 20.0, 20.0, 22.0]},
    "황혼": {"피증": [22.4, 22.4, 25.6, 25.6, 27.2], "note": "16스택기준"},
    "들불": {"치확": [14.0, 14.0, 16.0, 16.0, 18.0], "note": "화상보유적조건부"},
    "설산": {"추확": [16.0, 16.0, 18.0, 18.0, 20.0], "note": "빙결보유적조건부"},
    "여명": {"공증": [21.0, 21.0, 22.8, 22.8, 24.0], "note": "6스택기준"},
    "여명2": {"공증": 24.0, "note": "6스택기준"},
    "파멸": {"최종댐": [18.0, 18.0, 25.0, 27.0, 29.0], "note": "궁극기사용후20초"},
    "파멸2": {"최종댐": 29.0},
    "집념": {"캐속": [15.0, 15.0, 15.0, 15.0, 25.0], "피증": [8.0, 8.0, 10.0, 12.0, 14.0]},
    "집념2": {"캐속": 25.0, "피증": 14.0},
    "해결사": {"공속": [21.0, 21.0, 30.0, 33.0, 36.0], "추확": [21.0, 21.0, 30.0, 33.0, 36.0]},
    "해결사2": {"공속": 36.0, "추확": 36.0},
    # 엠블럼 룬
    "아득한빛": {"치확": [5.0, 5.0, 5.0], "치피": [10.0, 10.0, 10.0], "피증": [5.0, 7.0, 7.0],
                 "각성치확": 20.0, "각성치피": [50.0, 50.0, 62.0], "note": "각성시 치확+20%, 치피+50/62%"},
    "현란함": {"치확": 10.0, "치피": 30.0},
    "흩날리는검": {"공속": [24.0, 24.0, 27.0], "추확": [24.0, 24.0, 27.0],
                   "각성공격력": [55.0, 60.0, 60.0], "note": "각성시공격력증가"},
    "산맥군주": {"강피": [8.0, 10.0, 10.0], "note": "각성시강피대폭증가"},
    "부서진하늘": {"연피": [8.0, 10.0, 10.0], "쿨감": [8.0, 10.0, 10.0], "note": "각성시연피대폭증가"},
    "갈라진땅": {"추확": [12.0, 14.0, 14.0], "note": "각성시추확증가및추가공격"},
    "무자비한포식자": {"피증": [21.0, 23.0, 23.0], "note": "각성시스킬피해대폭증가및쿨초기화"},
    "대마법사": {"캐속": [14.0, 14.0, 16.0], "note": "각성시공격력+캐속증가"},
}


@dataclass
class DamageInput:
    """데미지 계산에 필요한 입력값"""
    # 클래스
    class_name: str = ""

    # 기본 스탯 (스탯창 기준)
    stat_atk: int = 0           # 스탯창 공격력 (A*B rounddown 결과)

    # 인챈트 공증 (%)
    enchant_atk_pct: float = 0.0   # 공증 인챈트 %

    # 스탯
    crit: int = 0               # 치명타 스탯
    multi: int = 0              # 멀티히트(광역강화) 스탯
    strong: int = 0             # 강타강화 스탯
    combo: int = 0              # 콤보강화 스탯
    add_hit: int = 0            # 추가타 스탯
    ult: int = 0                # 궁극기 스탯

    # 피해 증가 (%)
    skill_dmg_pct: float = 0.0  # 스킬 피해 %
    helm_pct: float = 5.4       # 헬리오도르 %  (기본 5.4)
    healer_pct: float = 0.0     # 힐러계열 버프 %

    # 받피증 (%)
    armor_break_pct: float = 0.0   # 방어구파괴 %
    synergy_debuff_pct: float = 0.0  # 시너지 받피증 %

    # 강화류 (%)
    multi_dmg_pct: float = 0.0  # 멀티히트 피해 %
    strong_dmg_pct: float = 0.0  # 강타 피해 %
    combo_dmg_pct: float = 0.0  # 콤보 피해 %
    skill_type_dmg_pct: float = 0.0  # 스킬 피해 %

    # 보석 태그 피해 %
    gem_pct: float = 0.0

    # 치명타 관련 (%)
    rune_crit_rate: float = 0.0   # 룬 치확 %
    char_crit_rate: float = 0.0   # 캐릭 치확증 %
    crit_rate_bonus: float = 0.0  # 치확 보너스 (레이드 등) %
    crit_dmg_pct: float = 0.0     # 치명타 피해 %
    char_crit_dmg: float = 0.0    # 캐릭 치피증 %

    # 무방비 관련
    break_stat: int = 1200       # 브레이크 스탯 (기본1200)
    unguarded_pct: float = 0.0   # 무방비 피해 %
    is_breakthrough: bool = False  # 브레이크익스텐드 여부
    break_type: str = "없음"      # 브레이크 종류

    # 방어력 감소/무시
    boss_def: int = 30           # 보스 방어력 (기본 허수아비 30)
    def_reduce_pct: float = 0.0  # 방어력 감소/무시율 %

    # 카운터
    is_counter: bool = False

    # 추가타 관련 (%)
    rune_addl_rate: float = 0.0   # 룬 추확 %
    galdang_addl_dmg: float = 0.0  # 갈라진땅 추가대미지 %
    ilreong_addl_dmg: float = 0.0  # 일렁/천체 추가대미지 %

    # 최종대미지 증가 (%)
    final_dmg_pct: float = 0.0   # 최종대미지증가스킬 %

    # 스킬 계수
    skill_coeff: float = 1.0     # 스킬 계수 (소수, 예: 1.44)

    # 스킬 계수 강화 H항 (곱연산/합연산 불명, 일단 합연산으로 처리)
    skill_coeff_enhance: float = 0.0  # H항 %

    # 기타 룬 효과
    rune_list: list = field(default_factory=list)  # 입력된 룬 목록

    # 클래스 자버프 옵션
    is_focus: bool = True        # 집중상태 여부 (검술사)
    sharp_eye_stack: int = 10   # 날카로운눈 스택 (검술사)
    burning_soul_stage: int = 3  # 버닝소울 단계 (화염술사)
    is_awakened: bool = False    # 각성 상태 여부

    # 보복 스택 (대검전사)
    revenge_stack: int = 0


def calc_A_from_stat(stat_atk: int) -> float:
    """스탯창 공격력 = rounddown(A*B, 0) → 그대로 사용"""
    return float(stat_atk)


def calc_B(enchant_atk_pct: float) -> float:
    """공증 B = 1 + 공증합%"""
    return 1.0 + enchant_atk_pct / 100.0


def calc_C(inp: DamageInput) -> float:
    """
    피증 C = 주피증배율 * 받피증배율
    주피증 = (1 + 스위/8500) * (1 + 스킬피해%) + 헬리오% + 일부스킬피증% + 템주피증% + 시너지대미지증가%
    받피증 = 1 + 방어구파괴% + 시너지받피증%
    """
    # 스위(스킬위력) - 현재 입력 없음, 0으로 처리
    sw = 0
    sw_factor = (1 + sw / 8500)

    # 스킬 피해%
    skill_factor = 1 + inp.skill_dmg_pct / 100.0

    # 주피증 기본
    main_dmg = sw_factor * skill_factor

    # 헬리오 + 기타 피증 합산 (합연산)
    additive = inp.helm_pct / 100.0 + inp.healer_pct / 100.0

    # 주피증 최종
    main_dmg_total = main_dmg + additive

    # 받피증
    recv_dmg = 1.0 + inp.armor_break_pct / 100.0 + inp.synergy_debuff_pct / 100.0

    return main_dmg_total * recv_dmg


def calc_D(inp: DamageInput) -> float:
    """
    강화류 D = 1 + 연타강화배율 + 강타강화배율 + 광역강화배율 + 콤보강화배율
    각 배율 = (1 + 스탯/8500) * (1 + 피해%) - 1
    콤보배율 = [(1 + 콤보/17500) * (1 + 콤보피해%) - 1] * (n/4)
    """
    # 멀티히트(광역)
    multi_rate = (1 + inp.multi / 8500) * (1 + inp.multi_dmg_pct / 100.0) - 1

    # 강타
    strong_rate = (1 + inp.strong / 8500) * (1 + inp.strong_dmg_pct / 100.0) - 1

    # 콤보 (n=4 기본값 = 100콤보 이상)
    combo_n = 4
    combo_rate = ((1 + inp.combo / 17500) * (1 + inp.combo_dmg_pct / 100.0) - 1) * (combo_n / 4)

    return 1.0 + multi_rate + strong_rate + combo_rate


def calc_E(gem_pct: float) -> float:
    """보석 E = 1 + 보석태그댐증%"""
    return 1.0 + gem_pct / 100.0


def calc_crit_rate(inp: DamageInput, class_buffs: dict) -> float:
    """
    치명타 확률 = MIN(0.5 - 1/(2 + 치명타/1000) + 룬치확% + 캐릭크확증% + 치확보너스%, 100%)
    """
    base = 0.5 - 1.0 / (2.0 + inp.crit / 1000.0)
    total = base + inp.rune_crit_rate / 100.0 + inp.char_crit_rate / 100.0 + inp.crit_rate_bonus / 100.0

    # 클래스 자버프 - 집중상태 치확
    if inp.class_name == "검술사" and inp.is_focus:
        total += 40.0 / 100.0

    # 석궁사수 드라이빙포스 치확 (감전룬 시)
    # 도적 스닉어택
    if inp.class_name == "도적":
        total += 15.0 / 100.0  # 스닉어택 상시 가정

    return min(total, 1.0)


def calc_crit_dmg(inp: DamageInput, class_buffs: dict) -> float:
    """
    치명타 배율 = (1.4 + 치명타/5000) * (1 + 치명타피해% + 캐릭크댐증%)
    """
    base_multi = 1.4 + inp.crit / 5000.0
    dmg_factor = 1.0 + inp.crit_dmg_pct / 100.0 + inp.char_crit_dmg / 100.0

    # 클래스 자버프
    extra_crit_dmg = 0.0
    if inp.class_name == "검술사":
        if inp.is_focus:
            extra_crit_dmg += 30.0  # 집중상태
        extra_crit_dmg += 5.0  # 전투숙련
        extra_crit_dmg += inp.sharp_eye_stack * 3.0  # 날카로운눈
    elif inp.class_name == "석궁사수":
        extra_crit_dmg += 5.0  # 전투숙련

    dmg_factor = 1.0 + (inp.crit_dmg_pct + inp.char_crit_dmg + extra_crit_dmg) / 100.0

    return base_multi * dmg_factor


def calc_F_expected(crit_rate: float, crit_dmg: float) -> float:
    """
    치명타 기댓값 F = 1 + 치명타확률 * (치명타배율 - 1)
    """
    return 1.0 + crit_rate * (crit_dmg - 1.0)


def calc_G(inp: DamageInput) -> float:
    """
    무방비 G = (1 + 브레이크/5250) * (1 + 무방비피해%) + (무방비20% + 태그댐증합) * (브익시 2배)
    """
    base = (1 + inp.break_stat / 5250) * (1 + inp.unguarded_pct / 100.0)

    # 브레이크 종류별 태그댐증
    TAG_DMG = {
        "없음": 0.0,
        "블로우": 30.0,   # 강타10+연타10+화상5+감전5
        "빙결": 30.0,     # 강타10+연타10+동상5+감전5
        "매혹": 35.0,     # 강타10+연타10+정신5+신성5+암흑5
        "스턴": 30.0,     # 강타10+연타10+화상5+동상5
        "멘탈": 35.0,     # 강타10+연타10+중독5+출혈5+정신5
        "석화": 30.0,     # 강타10+연타10+신성5+암흑5
    }
    tag = TAG_DMG.get(inp.break_type, 0.0)
    unguarded_bonus = (20.0 + tag) / 100.0

    if inp.is_breakthrough:
        unguarded_bonus *= 2.0

    return base + unguarded_bonus


def calc_H(inp: DamageInput) -> float:
    """스킬 계수 강화 H = 1 + H항%"""
    return 1.0 + inp.skill_coeff_enhance / 100.0


def calc_I(boss_def: int, def_reduce_pct: float) -> float:
    """방어력감소율 I = 1 / (1 + 보스방어력 * (1-방감율%) / 10328)"""
    effective_def = boss_def * (1 - def_reduce_pct / 100.0)
    return 1.0 / (1.0 + effective_def / 10328.0)


def calc_J(is_counter: bool) -> float:
    """카운터 J = 1.1 (카운터 시)"""
    return 1.1 if is_counter else 1.0


def calc_K_expected(inp: DamageInput) -> float:
    """
    추가타 기댓값 K = 1 + [(1+추가타/13000)*(1+룬추확%)-1] * (1+갈땅추가대미지%) + (일렁,천체 추가대미지%)
    """
    addl_rate = (1 + inp.add_hit / 13000) * (1 + inp.rune_addl_rate / 100.0) - 1
    k = 1.0 + addl_rate * (1 + inp.galdang_addl_dmg / 100.0) + inp.ilreong_addl_dmg / 100.0

    # 도적 스닉어택 추확
    if inp.class_name == "도적":
        extra_addl = (1 + inp.add_hit / 13000) * (1 + (inp.rune_addl_rate + 15.0) / 100.0) - 1
        k = 1.0 + extra_addl * (1 + inp.galdang_addl_dmg / 100.0) + inp.ilreong_addl_dmg / 100.0

    return k


def calc_L(inp: DamageInput) -> float:
    """최종대미지 L = 1 + 최종대미지증가스킬%"""
    total = inp.final_dmg_pct

    # 화염술사 버닝소울
    if inp.class_name == "화염술사":
        bs_dmg = {1: 3.0, 2: 6.0, 3: 15.0}
        total += bs_dmg.get(inp.burning_soul_stage, 0.0)

    return 1.0 + total / 100.0


def calc_damage(inp: DamageInput, mode: str = "expected") -> dict:
    """
    최종 대미지 계산
    mode: "expected" = 기댓값, "nocrit" = 노크리, "crit" = 크리
    """
    class_buffs = CLASS_BUFFS.get(inp.class_name, {})

    # A: 스탯창 공격력 (= rounddown(A*B, 0))
    A_times_B = float(inp.stat_atk)

    # C: 피증
    C = calc_C(inp)

    # D: 강화류
    D = calc_D(inp)

    # E: 보석
    E = calc_E(inp.gem_pct)

    # F: 치명타
    crit_rate = calc_crit_rate(inp, class_buffs)
    crit_dmg = calc_crit_dmg(inp, class_buffs)

    if mode == "expected":
        F = calc_F_expected(crit_rate, crit_dmg)
    elif mode == "nocrit":
        F = 1.0
    else:  # crit
        F = crit_dmg

    # G: 무방비
    G = calc_G(inp)

    # H: 스킬계수강화
    H = calc_H(inp)

    # I: 방어력감소율
    I = calc_I(inp.boss_def, inp.def_reduce_pct)

    # J: 카운터
    J = calc_J(inp.is_counter)

    # K: 추가타
    if mode == "expected":
        K = calc_K_expected(inp)
    else:
        K = 1.0

    # L: 최종대미지
    L = calc_L(inp)

    # 스킬계수
    skill = inp.skill_coeff

    # 민댐/맥댐 = 0.95~1.05, 평균 1.0 사용
    dmg_variance = 1.0

    # 최종 계산
    raw = 2.0 * dmg_variance * A_times_B * C * D * E * F * G * H * I * J * K * L * skill
    final = math.ceil(raw)

    return {
        "damage": final,
        "crit_rate": round(crit_rate * 100, 2),
        "crit_dmg": round(crit_dmg * 100, 2),
        "crit_expected": round(calc_F_expected(crit_rate, crit_dmg) * 100 - 100, 2),
        "addl_rate": round(calc_K_expected(inp) * 100 - 100, 2),
        "C": round(C * 100 - 100, 2),
        "D": round(D * 100 - 100, 2),
        "G": round(G * 100, 2),
        "I": round(I * 100, 2),
        "L": round(L * 100 - 100, 2),
        "components": {
            "A_B": A_times_B,
            "C": round(C, 4),
            "D": round(D, 4),
            "E": round(E, 4),
            "F": round(F, 4),
            "G": round(G, 4),
            "H": round(H, 4),
            "I": round(I, 4),
            "J": round(J, 4),
            "K": round(K, 4),
            "L": round(L, 4),
            "skill": skill,
        }
    }


def parse_rune_list(rune_str: str) -> list:
    """룬 문자열 파싱: '검무2 아득2 섬세2' → ['검무2', '아득2', '섬세2']"""
    return rune_str.strip().split() if rune_str.strip() else []


def apply_rune_effects(inp: DamageInput, is_awakened: bool = False) -> DamageInput:
    """룬 효과를 DamageInput에 반영"""
    for rune_name in inp.rune_list:
        rune_key = rune_name.lower().replace("+", "").replace(" ", "")
        # 정확한 이름으로 찾기
        effect = None
        for k, v in RUNE_EFFECTS.items():
            if k.lower().replace("+", "").replace(" ", "") == rune_key:
                effect = v
                break
        if not effect:
            continue

        # 등급 처리: 숫자 접미사로 등급 인식
        # 2 = 전설 최고 (마지막 값)
        grade_idx = -1  # 기본: 마지막(최고)

        # 효과 적용
        for stat, val in effect.items():
            if stat in ("note", "각성치확", "각성치피", "각성공격력", "각성추가댐"):
                continue

            v = val[grade_idx] if isinstance(val, list) else val

            # 각성 여부에 따른 분기
            if stat == "치확":
                if is_awakened and "각성치확" in effect:
                    v = effect["각성치확"]
                inp.rune_crit_rate += v
            elif stat == "치피":
                if is_awakened and "각성치피" in effect:
                    av = effect["각성치피"]
                    v = av[grade_idx] if isinstance(av, list) else av
                inp.crit_dmg_pct += v
            elif stat == "추확":
                if is_awakened and "각성추가댐" in effect:
                    inp.ilreong_addl_dmg += effect["각성추가댐"]
                else:
                    inp.rune_addl_rate += v
            elif stat == "피증":
                inp.helm_pct += v  # 피증에 합산
            elif stat == "공증":
                inp.enchant_atk_pct += v
            elif stat == "연피":
                inp.multi_dmg_pct += v
            elif stat == "강피":
                inp.strong_dmg_pct += v
            elif stat == "최종댐":
                inp.final_dmg_pct += v
            elif stat == "공속":
                pass  # 공속은 현재 계산식에 미포함
            elif stat == "캐속":
                pass  # 캐속도 미포함

    return inp


def format_result(inp: DamageInput, result_normal: dict, result_break: dict,
                  result_awake: dict, result_break_awake: dict) -> str:
    """결과 포매팅"""
    class_name = inp.class_name or "미지정"
    runes = " ".join(inp.rune_list) if inp.rune_list else "없음"

    lines = []
    lines.append(f"📊 [{class_name}] 배율 계산 결과")
    lines.append("")

    # 치확/추확
    lines.append(f"💥 치확: {result_normal['crit_rate']}% / {result_awake['crit_rate']}% (비각성/각성)")
    lines.append(f"❄️ 추확: {result_normal['addl_rate']:.2f}% / {result_awake['addl_rate']:.2f}% (비각성/각성)")
    lines.append("")

    # 기댓값 배율 (스킬계수=1 기준 %)
    def to_pct(dmg, atk):
        if atk == 0:
            return 0.0
        return round(dmg / atk * 100, 0)

    atk = inp.stat_atk if inp.stat_atk > 0 else 1

    n = to_pct(result_normal["damage"], atk)
    a = to_pct(result_awake["damage"], atk)
    b = to_pct(result_break["damage"], atk)
    ba = to_pct(result_break_awake["damage"], atk)

    lines.append(f"⚔️ 총 기댓값 배율 (스킬계수×100%):")
    lines.append(f"  비각성: {n:.0f}%  |  각성: {a:.0f}%")
    lines.append(f"  브익비각성: {b:.0f}%  |  브익각성: {ba:.0f}%")
    lines.append("")

    # 세부 정보
    lines.append("⚙️ 세부 정보 (비각성 기준)")
    lines.append(f"  피증(C): +{result_normal['C']:.1f}%")
    lines.append(f"  강화류(D): +{result_normal['D']:.1f}%")
    lines.append(f"  치명타 기댓값(F): +{result_normal['crit_expected']:.1f}%")
    lines.append(f"  무방비배율(G): {result_normal['G']:.1f}%")
    lines.append(f"  방감율(I): {result_normal['I']:.1f}%")
    lines.append(f"  최종댐증(L): +{result_normal['L']:.1f}%")
    lines.append("")
    lines.append(f"📋 적용 룬: {runes}")

    return "\n".join(lines)
