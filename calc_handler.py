"""
/배율 명령어 처리 - 최적 스탯 제안 포함
"""
import re
import copy
from damage_calc import (
    DamageInput, calc_damage, apply_rune_effects,
    CLASS_BUFFS, PENDING_CLASSES
)
from stat_optimizer import suggest_optimal_stats

SUPPORTED_CLASSES = list(CLASS_BUFFS.keys())
ALL_CLASSES = SUPPORTED_CLASSES + PENDING_CLASSES

STAT_KEYWORDS = {
    "연": "multi",
    "강": "strong",
    "치": "crit",
    "추": "add_hit",
    "스": "ult",
    "콤": "combo",
}

BOSS_DEF_PRESETS = {
    "허수아비": 30,
    "글라스": 6410,
    "서큐버스": 6410,
    "어비스지옥2": 9153,
    "바리어비스": 15903,
}


def parse_command(text: str) -> dict:
    text = re.sub(r"^/(배율|계산)\s*", "", text.strip())
    tokens = text.split()

    result = {"class_name": "", "stats": {}, "runes": [], "options": {}}
    i = 0

    if tokens and tokens[0] in ALL_CLASSES:
        result["class_name"] = tokens[0]
        i = 1

    stats, runes, options = {}, [], {}

    while i < len(tokens):
        token = tokens[i]; i += 1

        if token in BOSS_DEF_PRESETS:
            options["boss_def"] = BOSS_DEF_PRESETS[token]; continue
        if token in ("각성", "각성O"): options["is_awakened"] = True; continue
        if token.startswith("브레이크") and len(token) > 4:
            options["break_type"] = token[4:]; options["is_breakthrough"] = True; continue
        if token == "브익": options["is_breakthrough"] = True; continue
        if token in ("카운터", "카"): options["is_counter"] = True; continue
        if token in ("비집중", "집중X"): options["is_focus"] = False; continue
        if token in ("최적화X", "노최적화"): options["no_optimize"] = True; continue

        if token.startswith("버닝") and len(token) == 3:
            try: options["burning_soul_stage"] = int(token[2:]); continue
            except: pass
        if token.startswith("눈") and len(token) > 1:
            try: options["sharp_eye_stack"] = int(token[1:]); continue
            except: pass

        # 스탯 파싱
        matched = False
        for key, stat_name in STAT_KEYWORDS.items():
            if token.startswith(key) and len(token) > len(key):
                try:
                    stats[stat_name] = float(token[len(key):]); matched = True; break
                except: pass
        if matched: continue

        # 특수 파라미터
        for prefix, key in [("공격력","stat_atk"), ("헬리","helm_pct"), ("힐러","healer_pct"),
                              ("방파","armor_break_pct"), ("계수","skill_coeff")]:
            if token.startswith(prefix) and len(token) > len(prefix):
                try:
                    val = float(token[len(prefix):]); stats[key] = val; matched = True; break
                except: pass
        if matched: continue

        for prefix, key in [("보방","boss_def"), ("브스","break_stat"),
                              ("방감","def_reduce_pct")]:
            if token.startswith(prefix) and len(token) > len(prefix):
                try:
                    options[key] = float(token[len(prefix):]); matched = True; break
                except: pass
        if matched: continue

        runes.append(token)

    result["stats"] = stats
    result["runes"] = runes
    result["options"] = options
    return result


def build_input(parsed: dict, is_awakened: bool = False, breakthrough: bool = False) -> DamageInput:
    s = parsed.get("stats", {})
    o = parsed.get("options", {})
    return DamageInput(
        class_name=parsed.get("class_name", ""),
        stat_atk=int(s.get("stat_atk", 10000)),
        enchant_atk_pct=float(s.get("enchant_atk_pct", 0.0)),
        crit=int(s.get("crit", 0)),
        multi=int(s.get("multi", 0)),
        strong=int(s.get("strong", 0)),
        combo=int(s.get("combo", 0)),
        add_hit=int(s.get("add_hit", 0)),
        ult=int(s.get("ult", 0)),
        helm_pct=float(s.get("helm_pct", 5.4)),
        healer_pct=float(s.get("healer_pct", 0.0)),
        armor_break_pct=float(s.get("armor_break_pct", 0.0)),
        boss_def=int(o.get("boss_def", 30)),
        def_reduce_pct=float(o.get("def_reduce_pct", 0.0)),
        is_counter=bool(o.get("is_counter", False)),
        break_stat=int(o.get("break_stat", 1200)),
        is_breakthrough=breakthrough or bool(o.get("is_breakthrough", False)),
        break_type=o.get("break_type", "없음"),
        skill_coeff=float(o.get("skill_coeff", 1.0)),
        burning_soul_stage=int(o.get("burning_soul_stage", 3)),
        is_focus=bool(o.get("is_focus", True)),
        sharp_eye_stack=int(o.get("sharp_eye_stack", 10)),
        is_awakened=is_awakened,
        rune_list=parsed.get("runes", []),
    )


def calc_four(parsed: dict) -> dict:
    """비각성/각성/브익비각성/브익각성 4가지 계산"""
    results = {}
    for awake in (False, True):
        for brk in (False, True):
            inp = build_input(parsed, is_awakened=awake, breakthrough=brk)
            inp = apply_rune_effects(inp, is_awakened=awake)
            r = calc_damage(inp, mode="expected")
            key = f"{'각성' if awake else '비각성'}{'_브익' if brk else ''}"
            results[key] = {"inp": inp, "result": r}
    return results


def format_result(parsed: dict, four: dict) -> str:
    class_name = parsed.get("class_name", "?")
    stats = parsed.get("stats", {})
    runes_str = " ".join(parsed.get("runes", [])) or "없음"
    no_opt = parsed.get("options", {}).get("no_optimize", False)

    inp_n = four["비각성"]["inp"]
    inp_a = four["각성"]["inp"]
    r_n  = four["비각성"]["result"]
    r_a  = four["각성"]["result"]
    r_bn = four["비각성_브익"]["result"]
    r_ba = four["각성_브익"]["result"]

    atk = inp_n.stat_atk if inp_n.stat_atk > 0 else 10000

    def pct(r): return round(r["damage"] / atk * 100, 0)

    n_pct, a_pct = pct(r_n), pct(r_a)
    bn_pct, ba_pct = pct(r_bn), pct(r_ba)

    cr_n, cr_a = r_n["crit_rate"], r_a["crit_rate"]
    ar_n, ar_a = r_n["addl_rate"], r_a["addl_rate"]

    lines = []
    lines.append(f"📊 [{class_name}] 배율 계산 결과")
    lines.append("")
    lines.append(f"📈 스탯: 연{int(stats.get('multi',0))} 강{int(stats.get('strong',0))} 치{int(stats.get('crit',0))} 추{int(stats.get('add_hit',0))} 스{int(stats.get('ult',0))}")
    lines.append(f"✅ 적용룬: {runes_str}")
    lines.append("")
    lines.append("🧾 결과 (비각성/ 각성/ 브익비각성/ 브익각성)")
    lines.append(f"  💥 치확: {cr_n}% . {cr_a}% . {cr_n}% . {cr_a}%")
    lines.append(f"  ❄️ 추확: {ar_n:.2f}% . {ar_a:.2f}% . {ar_n:.2f}% . {ar_a:.2f}%")
    lines.append(f"  ⚔️ 기댓값: {n_pct:.0f}% . {a_pct:.0f}% . {bn_pct:.0f}% . {ba_pct:.0f}%")
    lines.append("")

    # 세부 정보
    lines.append("------------------------------")
    lines.append("⚙️ 세부 정보 (비각성/ 각성/ 브익비각성/ 브익각성)")
    lines.append("")

    enc_n = round(inp_n.enchant_atk_pct, 1)
    enc_a = round(inp_a.enchant_atk_pct, 1)
    lines.append(f"공증 수치: {enc_n}% . {enc_a}% . {enc_n}% . {enc_a}%")

    c_n, c_a = round(r_n['C'], 1), round(r_a['C'], 1)
    cb_n, cb_a = round(r_bn['C'], 1), round(r_ba['C'], 1)
    lines.append(f"피증 수치: +{c_n}% . +{c_a}% . +{cb_n}% . +{cb_a}%")

    lines.append(f"치명타 확률: {cr_n}% . {cr_a}% . {cr_n}% . {cr_a}%")
    ct_n, ct_a = round(r_n['crit_dmg'], 1), round(r_a['crit_dmg'], 1)
    lines.append(f"치명타 배율: {ct_n}% . {ct_a}% . {ct_n}% . {ct_a}%")
    ce_n, ce_a = round(r_n['crit_expected'], 1), round(r_a['crit_expected'], 1)
    lines.append(f"치명타 기댓값: +{ce_n}% . +{ce_a}% . +{ce_n}% . +{ce_a}%")

    lines.append(f"추가타 확률: {ar_n:.2f}% . {ar_a:.2f}% . {ar_n:.2f}% . {ar_a:.2f}%")

    d_n = round(r_n['D'] - 1, 4) * 100
    lines.append(f"강화류 배율: {round(r_n['D']*100,1)}%")

    g_n, g_a = round(r_n['G']*100,1), round(r_a['G']*100,1)
    g_bn, g_ba = round(r_bn['G']*100,1), round(r_ba['G']*100,1)
    lines.append(f"무방비 배율: {g_n}% . {g_a}% . {g_bn}% . {g_ba}%")

    lines.append(f"방감율(I): {r_n['I']:.1f}%")
    lines.append(f"최종댐증(L): +{r_n['L']:.1f}%")

    # 클래스 자버프 노트
    cb = CLASS_BUFFS.get(class_name, {})
    if cb.get("note"):
        lines.append("")
        lines.append(f"⚠️ {cb['note']}")

    # 최적 스탯 제안
    if not no_opt:
        lines.append("")
        lines.append("------------------------------")
        lines.append(suggest_optimal_stats(inp_n))

    return "\n".join(lines)


def handle_calc_command(text: str) -> str:
    if text.strip() in ("/배율", "/계산", "/배율 도움말", "/계산 도움말", "/배율도움말"):
        return get_help_text()

    parsed = parse_command(text)

    if not parsed.get("class_name"):
        return (
            f"❌ 클래스명을 입력해주세요.\n\n"
            f"✅ 지원: {', '.join(SUPPORTED_CLASSES)}\n"
            f"🔜 예정: {', '.join(PENDING_CLASSES)}\n\n"
            f"예시:\n/배율 검술사 연3500 강2000 치7500 추1200 스3000 검무2 아득2"
        )

    if parsed["class_name"] in PENDING_CLASSES:
        return f"⏳ {parsed['class_name']}은 준비 중이에요!\n지원 클래스: {', '.join(SUPPORTED_CLASSES)}"

    stats = parsed.get("stats", {})
    if not any(stats.get(k, 0) > 0 for k in ["crit", "multi", "strong", "add_hit"]):
        return "⚠️ 스탯을 입력해주세요.\n예: /배율 검술사 연3500 강2000 치7500 추1200 스3000"

    try:
        four = calc_four(parsed)
        return format_result(parsed, four)
    except Exception as e:
        return f"⚠️ 계산 오류: {str(e)}"


def get_help_text() -> str:
    return (
        "📖 배율 계산기 사용법\n\n"
        f"✅ 지원 클래스:\n{', '.join(SUPPORTED_CLASSES)}\n\n"
        f"🔜 추가 예정:\n{', '.join(PENDING_CLASSES)}\n\n"
        "📝 형식:\n"
        "/배율 [클래스] [스탯] [룬목록]\n\n"
        "📌 스탯:\n"
        "  연 강 치 추 스 콤 (+ 숫자)\n"
        "  예: 연3500 강2000 치7500 추1200 스3000\n\n"
        "📌 옵션:\n"
        "  각성 / 브익 / 카운터\n"
        "  계수X.XX  헬리XX  힐러XX\n"
        "  방파XX  보방XXXX\n"
        "  버닝1/2/3  비집중  눈N\n"
        "  최적화X (최적 스탯 생략)\n\n"
        "📌 보스 프리셋:\n"
        "  허수아비 글라스 어비스지옥2 바리어비스\n\n"
        "💡 예시:\n"
        "/배율 검술사 연3500 강2000 치7500 추1200 스3000 검무2 아득2 섬세2 압도2 바빛 일렁2 황혼2 장신구2 장신구2 장신구2"
    )
