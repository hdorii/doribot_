"""
최적 스탯 제안 모듈
연타/강타/치명타/추가타/궁극기 스탯 조합 중 기댓값 배율이 가장 높은 조합 탐색
"""
import copy
from damage_calc import DamageInput, calc_damage, apply_rune_effects

# 탐색할 스탯 총합 (연+강+치+추+스)
# 실제로는 장비에서 나오는 스탯이 한정되어 있으나,
# 총합을 고정하고 최적 배분을 찾는 방식으로 구현

def make_base_input(inp: DamageInput) -> DamageInput:
    """기본 입력값에서 스탯만 0으로 초기화"""
    base = copy.deepcopy(inp)
    base.crit = 0
    base.multi = 0
    base.strong = 0
    base.add_hit = 0
    base.ult = 0
    return base


def calc_expected_ratio(inp: DamageInput, is_awakened: bool = False) -> float:
    """배율 기댓값 계산 (비각성+각성 평균, 브익 제외)"""
    inp2 = copy.deepcopy(inp)
    inp2 = apply_rune_effects(inp2, is_awakened=False)
    r_normal = calc_damage(inp2, mode="expected")

    inp3 = copy.deepcopy(inp)
    inp3 = apply_rune_effects(inp3, is_awakened=True)
    r_awake = calc_damage(inp3, mode="expected")

    # 비각성 + 각성 평균
    return (r_normal["damage"] + r_awake["damage"]) / 2.0


def optimize_stats(
    inp: DamageInput,
    total_stat: int,
    fix_crit: int = None,
    fix_addl: int = None,
    step: int = 100,
) -> dict:
    """
    총합 스탯을 연타/강타/치명타/추가타/궁극기에 배분하여 최적 조합 탐색
    fix_crit: 치명타 고정값 (None이면 자유 탐색)
    fix_addl: 추가타 고정값 (None이면 자유 탐색)
    step: 탐색 간격 (기본 100)
    """
    base = make_base_input(inp)
    best_ratio = 0.0
    best_stats = {}

    # 탐색 범위 설정
    crit_range = [fix_crit] if fix_crit is not None else range(0, total_stat + 1, step)
    addl_range = [fix_addl] if fix_addl is not None else range(0, total_stat + 1, step)

    for crit in crit_range:
        for addl in addl_range:
            remaining = total_stat - crit - addl
            if remaining < 0:
                continue

            # 남은 스탯을 연타/강타에 배분 (궁극기는 배율에 직접 기여 적어 제외)
            # 연타:강타 비율 탐색
            for multi in range(0, remaining + 1, step):
                strong = remaining - multi
                if strong < 0:
                    continue

                test = copy.deepcopy(base)
                test.crit = crit
                test.multi = multi
                test.strong = strong
                test.add_hit = addl
                test.ult = 0

                ratio = calc_expected_ratio(test)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_stats = {
                        "연": multi,
                        "강": strong,
                        "치": crit,
                        "추": addl,
                        "스": 0,
                    }

    return best_stats


def suggest_optimal_stats(inp: DamageInput, total_stat: int = None) -> str:
    """
    최적 스탯 제안 텍스트 생성
    현재 스탯 총합 기준으로 탐색
    """
    if total_stat is None:
        total_stat = inp.crit + inp.multi + inp.strong + inp.add_hit + inp.ult

    if total_stat == 0:
        return "❌ 스탯 정보가 없어 최적화를 진행할 수 없어요."

    lines = []
    lines.append(f"💡 최적 스탯 제안 (총합 {total_stat} 기준)")
    lines.append("")

    # 3가지 케이스 탐색
    cases = [
        ("스탯고정X", None, None),
        ("치명고정O", inp.crit, None),
        ("추타고정O", None, inp.add_hit),
    ]

    for label, fix_crit, fix_addl in cases:
        best = optimize_stats(inp, total_stat, fix_crit=fix_crit, fix_addl=fix_addl, step=100)
        if best:
            lines.append(f"  ({label})")
            lines.append(
                f"  연{best['연']} 강{best['강']} 치{best['치']} 추{best['추']} 스{best['스']}"
            )

    lines.append("")
    lines.append("  - 연타/강타는 항상 높은 쪽으로 몰빵하라고 뜹니다.")
    lines.append("  - 절대적인 정답이 아니니 참고만 부탁드립니다.")

    return "\n".join(lines)
