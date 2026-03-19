"""
최적 스탯 제안 모듈 - 빠른 버전
3중 for 대신 수학적 근사 + 굵은 step으로 빠르게 탐색
"""
import copy
from damage_calc import DamageInput, calc_damage, apply_rune_effects


def make_base_input(inp: DamageInput) -> DamageInput:
    base = copy.deepcopy(inp)
    base.crit = 0
    base.multi = 0
    base.strong = 0
    base.add_hit = 0
    base.ult = 0
    # 룬 효과는 이미 반영돼 있으므로 rune_list 비움 (중복 방지)
    base.rune_list = []
    return base


def calc_ratio(inp: DamageInput) -> float:
    """기댓값 배율 (비각성+각성 평균)"""
    r1 = calc_damage(inp, mode="expected")
    inp2 = copy.deepcopy(inp)
    inp2.is_awakened = True
    r2 = calc_damage(inp2, mode="expected")
    return (r1["damage"] + r2["damage"]) / 2.0


def optimize_fast(base: DamageInput, total: int,
                   fix_crit=None, fix_addl=None) -> dict:
    """
    빠른 최적화: 2단계 탐색
    1단계: step=500으로 대략 찾기
    2단계: 1단계 결과 주변 step=100으로 정밀화
    """
    best_ratio = 0.0
    best = {"연": 0, "강": 0, "치": 0, "추": 0, "스": 0}

    def search(step):
        nonlocal best_ratio, best
        crit_vals = [fix_crit] if fix_crit is not None else range(0, total + 1, step)
        addl_vals = [fix_addl] if fix_addl is not None else range(0, total + 1, step)

        for crit in crit_vals:
            for addl in addl_vals:
                rem = total - crit - addl
                if rem < 0:
                    continue
                # 연타/강타는 한쪽에 몰빵하는 게 유리한 경향이 있으므로
                # 대표 비율만 탐색: 0/100, 25/75, 50/50, 75/25, 100/0
                for multi_ratio in (0, 0.25, 0.5, 0.75, 1.0):
                    multi = round(rem * multi_ratio / step) * step
                    strong = rem - multi
                    if strong < 0 or multi < 0:
                        continue

                    t = copy.deepcopy(base)
                    t.crit = crit
                    t.multi = multi
                    t.strong = strong
                    t.add_hit = addl
                    t.ult = 0

                    ratio = calc_ratio(t)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best = {"연": multi, "강": strong, "치": crit, "추": addl, "스": 0}

    # 1단계: 굵은 탐색
    step1 = max(500, (total // 20 // 100) * 100)  # 총합의 1/20 단위, 최소 500
    search(step1)

    # 2단계: 최적 근처 정밀 탐색
    b_crit = best["치"] if fix_crit is None else fix_crit
    b_addl = best["추"] if fix_addl is None else fix_addl
    step2 = 100

    crit_vals2 = range(max(0, b_crit - step1), min(total, b_crit + step1) + 1, step2) \
        if fix_crit is None else [fix_crit]
    addl_vals2 = range(max(0, b_addl - step1), min(total, b_addl + step1) + 1, step2) \
        if fix_addl is None else [fix_addl]

    for crit in crit_vals2:
        for addl in addl_vals2:
            rem = total - crit - addl
            if rem < 0:
                continue
            for multi_ratio in (0, 0.25, 0.5, 0.75, 1.0):
                multi = round(rem * multi_ratio / step2) * step2
                strong = rem - multi
                if strong < 0 or multi < 0:
                    continue

                t = copy.deepcopy(base)
                t.crit = crit
                t.multi = multi
                t.strong = strong
                t.add_hit = addl
                t.ult = 0

                ratio = calc_ratio(t)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best = {"연": multi, "강": strong, "치": crit, "추": addl, "스": 0}

    return best


def suggest_optimal_stats(inp: DamageInput, total_stat: int = None) -> str:
    if total_stat is None:
        total_stat = inp.crit + inp.multi + inp.strong + inp.add_hit + inp.ult

    if total_stat == 0:
        return "❌ 스탯 정보가 없어 최적화를 진행할 수 없어요."

    base = make_base_input(inp)

    lines = []
    lines.append(f"💡 최적 스탯 제안 (총합 {total_stat} 기준)")
    lines.append("")

    cases = [
        ("스탯고정X", None, None),
        ("치명고정O", inp.crit, None),
        ("추타고정O", None, inp.add_hit),
    ]

    for label, fix_crit, fix_addl in cases:
        best = optimize_fast(base, total_stat, fix_crit=fix_crit, fix_addl=fix_addl)
        lines.append(f"  ({label})")
        lines.append(f"  연{best['연']} 강{best['강']} 치{best['치']} 추{best['추']} 스{best['스']}")

    lines.append("")
    lines.append("  - 연타/강타는 항상 높은 쪽으로 몰빵하라고 뜹니다.")
    lines.append("  - 절대적인 정답이 아니니 참고만 부탁드립니다.")

    return "\n".join(lines)
