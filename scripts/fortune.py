#!/usr/bin/env python3
"""
八字算命 skill 核心脚本 v2
支持多人八字存储 + 联合分析
"""
import json
import os
import sys
import re
import subprocess
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SKILL_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_users():
    ensure_dir()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(data):
    ensure_dir()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_active():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"active": False, "names": []}


def save_active(data):
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_bazi(year, month, day, hour, minute, gender):
    """调用 suanzhun.net 接口获取八字"""
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://www.suanzhun.net/suanzhunbazi/bzi.php",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-F", f"xing=公历",
        "-F", f"nian={year}",
        "-F", f"yue={month}",
        "-F", f"ri={day}",
        "-F", f"hh={hour}",
        "-F", f"ff={minute}",
        "-F", "xuexing=123",
        "-F", f"xingbie={gender}",
        "--max-time", "30",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    html = result.stdout

    data = {}

    # 农历
    m = re.search(r'农历：(\d+)年(\d+)月(\d+)日(\w+)时', html)
    if m:
        data["lunar"] = {"year": int(m.group(1)), "month": int(m.group(2)), "day": int(m.group(3)), "hour": m.group(4)}

    # 八字
    m = re.search(r'生辰：([^<]+)<', html)
    if m:
        parts = m.group(1).strip().split()
        if len(parts) == 4:
            data["bazi"] = {"year": parts[0], "month": parts[1], "day": parts[2], "hour": parts[3]}

    # 五行
    m = re.search(r'五行：([^<]+)，', html)
    if m:
        data["wuxing"] = m.group(1).strip()

    # 命格
    m = re.search(r'命格：([^<]+)', html)
    if m:
        data["mingge"] = m.group(1).strip()

    # 旺衰
    m = re.search(r'旺衰：([^<]+)<', html)
    if m:
        data["wangshuai"] = m.group(1).strip()

    # 喜用
    m = re.search(r'喜用：([^<]+)', html)
    if m:
        data["xiyong"] = m.group(1).strip()

    # 阴阳
    m = re.search(r'阴阳：([^<]+)，', html)
    if m:
        data["yinyang"] = m.group(1).strip()

    # 星座
    m = re.search(r'星座：([^<]+)', html)
    if m:
        data["constellation"] = m.group(1).strip()

    # 称骨
    m = re.search(r'称骨：[^>]+>([^<]+)<', html)
    if m:
        data["chengguxiang"] = m.group(1).strip()

    # 命卦
    m = re.search(r'命卦：([^<]+)', html)
    if m:
        data["minggua"] = m.group(1).strip()

    # 空亡
    m = re.search(r'空亡：</div>\s*<div[^>]*>([^<]+)</div>', html)
    if m:
        data["kongwang"] = m.group(1).strip()

    # 神煞
    shensha = []
    for p in [r'天乙贵人', r'太极贵人', r'桃花', r'将星', r'财库', r'空亡', r'天罗', r'劫煞', r'驿马', r'童子']:
        if p in html:
            shensha.append(p)
    data["shensha"] = shensha

    # 起运时间
    m = re.search(r'出生.*?阳历(\d{4}-\d{2}-\d{2})后起运', html)
    if m:
        data["qiyun_date"] = m.group(1)

    # 大运（取前8个）
    dayun = []
    texts = re.findall(r'<span[^>]*>(\d{4})</span><br[^>]*>.*?<span[^>]*>([\w]+)</span>', html)
    seen = set()
    for year_str, gan in texts:
        key = (year_str, gan)
        if key not in seen and len(seen) < 10:
            seen.add(key)
            dayun.append({"year": int(year_str), "gan": gan})
    data["dayun"] = dayun[:8]

    # 命局天干/地支作用
    m = re.search(r'命局天干留意：([^<]+)', html)
    if m:
        data["mingju_gan"] = m.group(1).strip()
    m = re.search(r'命局地支留意：([^<]+)', html)
    if m:
        data["mingju_zhi"] = m.group(1).strip()

    # 婚姻
    marriage = {}
    m = re.search(r'婚期建议：([^<\n]+)', html)
    if m:
        marriage["婚期建议"] = m.group(1).strip()
    m = re.search(r'配偶方位：([^<]+)', html)
    if m:
        marriage["配偶方位"] = m.group(1).strip()
    m = re.search(r'配偶长相[^>]*>：([^<]+)', html)
    if m:
        marriage["配偶长相"] = m.group(1).strip()[:200]
    if marriage:
        data["marriage"] = marriage

    # 2026开运
    kaiyun = {}
    m = re.search(r'2026[^<]*躲星[^<]*时间：([^<]+)<', html)
    if m:
        kaiyun["躲星时间"] = m.group(1).strip()
    if kaiyun:
        data["kaiyun_2026"] = kaiyun

    return data


# ─── Commands ───────────────────────────────────────────────

def cmd_add():
    """fortune.py add <name> <year> <month> <day> <hour> <minute> <gender>"""
    args = sys.argv[2:]
    if len(args) < 7:
        print("Usage: fortune.py add <name> <year> <month> <day> <hour> <minute> <gender>")
        sys.exit(1)

    name, year, month, day, hour, minute, gender = args[0], args[1], args[2], args[3], args[4], args[5], args[6]
    users = load_users()

    if name in users:
        print(f"'{name}' 已存在，使用 update 命令更新。")
        sys.exit(1)

    bazi_data = fetch_bazi(year, month, day, hour, minute, gender)

    users[name] = {
        "birth": {"year": int(year), "month": int(month), "day": int(day), "hour": int(hour), "minute": int(minute), "gender": gender},
        "bazi": bazi_data,
        "fetched_at": datetime.now(TZ).isoformat()
    }
    save_users(users)
    print(f"✅ 已添加：{name}")
    print(json.dumps(users[name], ensure_ascii=False, indent=2))


def cmd_update():
    """fortune.py update <name> <year> <month> <day> <hour> <minute> <gender>"""
    args = sys.argv[2:]
    if len(args) < 7:
        print("Usage: fortune.py update <name> <year> <month> <day> <hour> <minute> <gender>")
        sys.exit(1)

    name, year, month, day, hour, minute, gender = args[0], args[1], args[2], args[3], args[4], args[5], args[6]
    users = load_users()

    bazi_data = fetch_bazi(year, month, day, hour, minute, gender)
    users[name] = {
        "birth": {"year": int(year), "month": int(month), "day": int(day), "hour": int(hour), "minute": int(minute), "gender": gender},
        "bazi": bazi_data,
        "fetched_at": datetime.now(TZ).isoformat()
    }
    save_users(users)
    print(f"✅ 已更新：{name}")
    print(json.dumps(users[name], ensure_ascii=False, indent=2))


def cmd_list():
    """fortune.py list - 列出所有已保存的八字"""
    users = load_users()
    if not users:
        print("还没有保存任何八字。请使用 add 命令添加。")
        return
    for name, data in users.items():
        bazi = data.get("bazi", {}).get("bazi", {})
        if isinstance(bazi, dict):
            bazi_str = " ".join(bazi.values())
        else:
            bazi_str = str(bazi)
        birth = data["birth"]
        print(f"• {name}：{birth['year']}年{birth['month']}月{birth['day']}日 {bazi_str} ({birth['gender']})")


def cmd_view():
    """fortune.py view [name] - 显示某人八字详情"""
    users = load_users()
    args = sys.argv[2:]
    if args:
        name = args[0]
    else:
        # 默认查看active用户
        active = load_active()
        if not active.get("names"):
            print("未指定姓名，且没有已激活的用户。")
            sys.exit(1)
        name = active["names"][0]

    if name not in users:
        print(f"未找到：{name}")
        sys.exit(1)

    u = users[name]
    birth = u["birth"]
    bazi = u.get("bazi", {})
    bazi_ganzhi = bazi.get("bazi", {})
    lunar = bazi.get("lunar", {})
    gender_display = "男" if birth["gender"] == "男" else "女"

    if isinstance(bazi_ganzhi, dict):
        bazi_str = " ".join(bazi_ganzhi.values())
    else:
        bazi_str = str(bazi_ganzhi)

    lines = [
        f"姓名：{name}",
        f"性别：{gender_display}",
        f"公历：{birth['year']}年{birth['month']}月{birth['day']}日{birth['hour']}点{birth['minute']}分",
        f"农历：{lunar.get('year', '?')}年{lunar.get('month', '?')}月{lunar.get('day', '?')}日{lunar.get('hour', '')}时",
        f"八字：{bazi_str}",
        f"五行：{bazi.get('wuxing', '')}",
        f"命格：{bazi.get('mingge', '')}",
        f"旺衰：{bazi.get('wangshuai', '')}",
        f"喜用：{bazi.get('xiyong', '')}",
        f"星座：{bazi.get('constellation', '')}",
        f"称骨：{bazi.get('chengguxiang', '')}",
        f"命卦：{bazi.get('minggua', '')}",
        f"空亡：{bazi.get('kongwang', '')}",
        f"神煞：{', '.join(bazi.get('shensha', []))}",
    ]
    print("\n".join(line for line in lines if line))


def cmd_remove():
    """fortune.py remove <name> - 删除某人八字"""
    users = load_users()
    args = sys.argv[2:]
    if not args:
        print("Usage: fortune.py remove <name>")
        sys.exit(1)
    name = args[0]
    if name not in users:
        print(f"未找到：{name}")
        sys.exit(1)
    del users[name]
    save_users(users)
    # 如果在active里也删掉
    active = load_active()
    if name in active.get("names", []):
        active["names"] = [n for n in active["names"] if n != name]
        save_active(active)
    print(f"✅ 已删除：{name}")


def cmd_active():
    """fortune.py active [name1,name2,...] - 设置当前激活的用户"""
    users = load_users()
    args = sys.argv[2:]

    if not args:
        active = load_active()
        if active.get("names"):
            print("当前激活：" + ", ".join(active["names"]))
        else:
            print("当前无激活用户")
        return

    names_input = args[0]
    if names_input.lower() == "none":
        names = []
    else:
        names = [n.strip() for n in names_input.split(",")]
        for n in names:
            if n not in users:
                print(f"错误：'{n}' 未找到，请先用 add 命令添加。")
                sys.exit(1)

    save_active({"active": True, "names": names})
    if names:
        print(f"✅ 已激活：{', '.join(names)}")
    else:
        print("✅ 已取消激活")


def cmd_status():
    """fortune.py status - 检查激活状态"""
    active = load_active()
    users = load_users()
    if not users:
        print("NOT_FOUND:无任何用户")
        return
    if not active.get("active") or not active.get("names"):
        print("NOT_ACTIVE")
        return
    # 检查激活的用户是否都还在
    for n in active["names"]:
        if n not in users:
            print(f"NOT_ACTIVE:{n}已删除")
            return
    names_str = ",".join(active["names"])
    print(f"ACTIVE:{names_str}")


def cmd_joint():
    """fortune.py joint [name1,name2] - 联合分析，默认用当前激活用户"""
    users = load_users()
    args = sys.argv[2:]

    if args:
        names = [n.strip() for n in args[0].split(",")]
    else:
        active = load_active()
        names = active.get("names", [])
        if not names:
            print("未指定用户，且无激活用户。请使用 active 或 joint name1,name2")
            sys.exit(1)

    if len(names) < 2:
        print("联合分析至少需要2个人。")
        sys.exit(1)

    data_list = []
    for name in names:
        if name not in users:
            print(f"未找到：{name}")
            sys.exit(1)
        data_list.append({"name": name, **users[name]})

    output = generate_joint_analysis(data_list)
    print(output)


def generate_joint_analysis(data_list):
    """生成两人或多人联合分析"""
    lines = ["━━━ 联合分析 ━━━"]

    for d in data_list:
        bazi = d["bazi"].get("bazi", {})
        if isinstance(bazi, dict):
            bazi_str = " ".join(bazi.values())
        else:
            bazi_str = str(bazi)
        gender = "男" if d["birth"]["gender"] == "男" else "女"
        lines.append(f"【{d['name']}】{gender} | {bazi_str} | {d['bazi'].get('mingge','')}")

    lines.append("━━━ 合冲刑害 ━━━")

    # 提取所有地支
    all_zhi = []
    for d in data_list:
        bazi = d["bazi"].get("bazi", {})
        if isinstance(bazi, dict):
            all_zhi.append({
                "name": d["name"],
                "year_zhi": bazi.get("year", "")[-1:] if len(bazi.get("year", "")) > 1 else "",
                "month_zhi": bazi.get("month", "")[-1:] if len(bazi.get("month", "")) > 1 else "",
                "day_zhi": bazi.get("day", "")[-1:] if len(bazi.get("day", "")) > 1 else "",
                "hour_zhi": bazi.get("hour", "")[-1:] if len(bazi.get("hour", "")) > 1 else "",
            })

    # 年支关系（祖辈/根基）
    year_zhi = [(d["name"], all_zhi[i]["year_zhi"]) for i, d in enumerate(data_list)]
    lines.append(f"年支关系：{analyze_zhi_relation([z for _, z in year_zhi])}（{', '.join([f'{n}{z}' for n,z in year_zhi])})")

    # 日支关系（夫妻/伴侣）
    day_zhi = [(d["name"], all_zhi[i]["day_zhi"]) for i, d in enumerate(data_list)]
    lines.append(f"日支关系：{analyze_zhi_relation([z for _, z in day_zhi])}（{', '.join([f'{n}{z}' for n,z in day_zhi])})")

    # 月支关系（父母/环境）
    month_zhi = [(d["name"], all_zhi[i]["month_zhi"]) for i, d in enumerate(data_list)]
    lines.append(f"月支关系：{analyze_zhi_relation([z for _, z in month_zhi])}")

    # 喜用五行是否相生
    wuxing_map = {"木": "木", "火": "火", "土": "土", "金": "金", "水": "水"}
    xiyong_list = []
    for d in data_list:
        xiyong = d["bazi"].get("xiyong", "")
        xiyong_list.append({"name": d["name"], "xiyong": xiyong, "wuxing": d["bazi"].get("wuxing", "")})

    # 五行互补
    if len(data_list) >= 2:
        wuxing_chars = []
        for d in data_list:
            bazi = d["bazi"].get("bazi", {})
            if isinstance(bazi, dict):
                wuxing_chars.append({"name": d["name"], "chars": "".join(bazi.values())})
        lines.append("")
        lines.append("━━━ 五行契合 ━━━")
        wuxing_summary = analyze_wuxing_compat([w["chars"] for w in wuxing_chars])
        lines.append(wuxing_summary)

    # 联合婚姻分析
    if len(data_list) == 2:
        lines.append("")
        lines.append("━━━ 婚配分析 ━━━")
        marriage_analysis = analyze_marriage_pair(data_list[0], data_list[1])
        lines.append(marriage_analysis)

    return "\n".join(lines)


def analyze_zhi_relation(zhi_list):
    """分析地支间的合冲刑害"""
    relations = []
    zhi = list(zhi_list)

    # 地支六合
    he_map = {"子丑":"合","寅亥":"合","卯戌":"合","辰酉":"合","巳申":"合","午未":"合"}
    # 地支六冲
    chong_map = {"子午":"冲","丑未":"冲","寅申":"冲","卯酉":"冲","辰戌":"冲","巳亥":"冲"}
    # 地支三合
    sanhe_map = {"申子辰":"水局","巳酉丑":"金局","寅午戌":"火局","亥卯未":"木局"}
    # 地支三会
    sanhui_map = {"寅卯辰":"木会","巳午未":"火会","申酉戌":"金会","亥子丑":"水会"}
    # 地支三刑
    xing_map = {"寅巳申":"三刑","丑戌未":"三刑","子卯":"刑","辰辰":"自刑","午午":"自刑","酉酉":"自刑","亥亥":"自刑"}

    for i in range(len(zhi)):
        for j in range(i+1, len(zhi)):
            a, b = zhi[i], zhi[j]
            key1, key2 = f"{a}{b}", f"{b}{a}"
            if key1 in he_map:
                relations.append(f"{a}{he_map[key1]}{b}（吉）")
            elif key1 in chong_map:
                relations.append(f"{a}{chong_map[key1]}{b}（冲）")
            elif key1 in xing_map:
                relations.append(f"{a}{xing_map[key1]}{b}（刑）")

    # 检查三合
    for pattern, name in sanhe_map.items():
        if all(z in pattern for z in zhi):
            relations.append(f"三合{name}（吉）")
    # 检查三会
    for pattern, name in sanhui_map.items():
        if all(z in pattern for z in zhi):
            relations.append(f"三会{name}（吉）")

    if not relations:
        return "无明显合冲刑害"
    return " / ".join(relations)


def analyze_wuxing_compat(chars_list):
    """分析五行契合度"""
    wuxing_element = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}

    elements = []
    for chars in chars_list:
        elems = set()
        for c in chars:
            if c in wuxing_element:
                elems.add(wuxing_element[c])
        elements.append(elems)

    # 检查是否相生
    sheng = {"木生火","火生土","土生金","金生水","水生木"}
    pairs = []
    for i in range(len(elements)):
        for j in range(i+1, len(elements)):
            ei, ej = elements[i], elements[j]
            # 是否一方能生另一方
            for e1 in ei:
                for e2 in ej:
                    if f"{e1}生{e2}" in sheng:
                        pairs.append(f"{list(chars_list[i])}生{list(chars_list[j])}")
                    if f"{e2}生{e1}" in sheng:
                        pairs.append(f"{list(chars_list[j])}生{list(chars_list[i])}")

    if not pairs:
        return "五行无明显相生关系，较为独立"
    return "五行相生：" + "、".join(pairs)


def analyze_marriage_pair(d1, d2):
    """分析两人婚配"""
    lines = []
    bazi1 = d1["bazi"].get("bazi", {})
    bazi2 = d2["bazi"].get("bazi", {})

    if isinstance(bazi1, dict) and isinstance(bazi2, dict):
        # 日支对日支
        zhi1 = bazi1.get("day", "")[-1:] if len(bazi1.get("day", "")) > 1 else ""
        zhi2 = bazi2.get("day", "")[-1:] if len(bazi2.get("day", "")) > 1 else ""

        relation = analyze_zhi_relation([zhi1, zhi2])
        lines.append(f"日支关系：{relation}（{d1['name']}:{zhi1} / {d2['name']}:{zhi2}）")

        # 年支对年支（祖辈/根基）
        year_zhi1 = bazi1.get("year", "")[-1:] if len(bazi1.get("year", "")) > 1 else ""
        year_zhi2 = bazi2.get("year", "")[-1:] if len(bazi2.get("year", "")) > 1 else ""
        year_rel = analyze_zhi_relation([year_zhi1, year_zhi2])
        lines.append(f"年支关系：{year_rel}（{d1['name']}:{year_zhi1} / {d2['name']}:{year_zhi2}）")

        # 喜用是否互补
        xiyong1 = d1["bazi"].get("xiyong", "")
        xiyong2 = d2["bazi"].get("xiyong", "")
        lines.append(f"喜用互补：{xiyong1[:30]} | {xiyong2[:30]}")

    # 婚姻神煞检查
    shensha1 = set(d1["bazi"].get("shensha", []))
    shensha2 = set(d2["bazi"].get("shensha", []))

    taohua_common = "桃花" in shensha1 and "桃花" in shensha2
    if taohua_common:
        lines.append("⚠️ 双方均带桃花，感情需注意经营")

    if "天乙贵人" in shensha1 and "天乙贵人" in shensha2:
        lines.append("✅ 双方均有天乙贵人，互助有缘")

    return "\n".join(lines) if lines else "（数据不足）"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fortune.py <add|update|list|view|remove|active|status|joint>")
        sys.exit(1)

    cmd = sys.argv[1]
    {
        "add": cmd_add,
        "update": cmd_update,
        "list": cmd_list,
        "view": cmd_view,
        "remove": cmd_remove,
        "active": cmd_active,
        "status": cmd_status,
        "joint": cmd_joint,
    }.get(cmd, lambda: print(f"Unknown: {cmd}"))()
