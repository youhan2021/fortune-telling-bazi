#!/usr/bin/env python3
"""
八字算命 skill 核心脚本
功能：获取八字、存储用户信息、判断是否首次/非首次
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
USER_FILE = os.path.join(DATA_DIR, "user.json")


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_user():
    ensure_dir()
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_user(data):
    ensure_dir()
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_bazi(year, month, day, hour, minute, gender):
    """调用 suanzhun.net 接口获取八字"""
    # minute 转换为 "ff" 字段，API 接受 "未知" 或具体分钟
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

    # 解析关键信息
    data = {}

    # 农历
    m = re.search(r'农历：(\d+)年(\d+)月(\d+)日(\w+)时', html)
    if m:
        data["lunar"] = {
            "year": int(m.group(1)),
            "month": int(m.group(2)),
            "day": int(m.group(3)),
            "hour": m.group(4)
        }

    # 生辰（八字）
    m = re.search(r'生辰：([^<]+)<', html)
    if m:
        parts = m.group(1).strip().split()
        if len(parts) == 4:
            data["bazi"] = {
                "year": parts[0],
                "month": parts[1],
                "day": parts[2],
                "hour": parts[3]
            }

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

    # 神煞（提取主要神煞）
    shensha = []
    for pattern in [r'天乙贵人', r'太极贵人', r'桃花', r'将星', r'财库',
                    r'空亡', r'天罗', r'劫煞', r'驿马', r'童子']:
        if pattern in html:
            shensha.append(pattern)
    data["shensha"] = shensha

    # 大运信息
    dayun = []
    m = re.search(r'出生.*?阳历(\d{4}-\d{2}-\d{2})后起运', html)
    if m:
        data["qiyun_date"] = m.group(1)

    # 提取大运天干地支
    dayun_matches = re.findall(
        r'<span style="[^"]*">(\w+)</span><span style="[^"]*">(\w+)</span>',
        html
    )
    # 大运出现在特定结构中，过滤掉其他天干地支
    in_dayun = False
    for match in re.finditer(r'<td[^>]*>大</td><td[^>]*>运</td>', html):
        in_dayun = True
        break

    # 解析大运列表（简化：直接取关键段落）
    dayun_section = re.search(
        r'class="layui-tab-title"[^>]*>(.*?)class="layui-tab-content"',
        html, re.DOTALL
    )
    if dayun_section:
        texts = re.findall(
            r'<span[^>]*>(\d{4})</span><br[^>]*>.*?<span[^>]*>([\w]+)</span>',
            dayun_section.group(1)
        )
        seen = set()
        for year_str, gan in texts:
            key = (year_str, gan)
            if key not in seen and len(seen) < 10:
                seen.add(key)
                dayun.append({"year": int(year_str), "gan": gan})

    data["dayun"] = dayun[:8] if dayun else []

    # 命局天干/地支作用
    m = re.search(r'命局天干留意：([^<]+)', html)
    if m:
        data["mingju_gan"] = m.group(1).strip()

    m = re.search(r'命局地支留意：([^<]+)', html)
    if m:
        data["mingju_zhi"] = m.group(1).strip()

    # 流年信息（2025-2034）
    liunian = {}
    liunian_section = re.search(
        r'id="liunian">.*?<div class="layui-tab-content">(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    if liunian_section:
        items = re.findall(
            r'<span[^>]*>(\d{4})</span><br[^>]*>.*?<span[^>]*>([\w]+)</span><span[^>]*>([\w]+)</span>',
            liunian_section.group(1)
        )
        for year, gan, zhi in items:
            if year not in liunian:
                liunian[year] = {"gan": gan, "zhi": zhi}

    data["liunian"] = liunian

    # 事业/五行吉祥方位建议
    suggestions = {}
    sections = [
        ("shui", r"属水数字、方位:[^<]+"),
        ("jin", r"属金数字、方位:[^<]+"),
        ("career", r"属水职业:[^<]+|属金职业:[^<]+"),
    ]
    for key, pattern in sections:
        m = re.search(pattern, html)
        if m:
            suggestions[key] = m.group(0).strip()[:200]

    if suggestions:
        data["suggestions"] = suggestions

    # 婚姻信息
    marriage = {}
    m = re.search(r'婚期建议：([^<\n]+)', html)
    if m:
        marriage["婚期建议"] = m.group(1).strip()
    m = re.search(r'生肖兔婚配建议：([^<]+)', html)
    if m:
        marriage["婚配建议"] = m.group(1).strip()
    m = re.search(r'桃花[^>]*>婚姻[^>]*>([^<]+)', html)
    if m:
        marriage["桃花分析"] = m.group(1).strip()[:200]
    m = re.search(r'婚姻忠诚分析：[^>]+>.*?<font[^>]*>([^<]+)', html, re.DOTALL)
    if m:
        marriage["忠诚分析"] = m.group(1).strip()[:200]
    m = re.search(r'配偶方位：([^<]+)', html)
    if m:
        marriage["配偶方位"] = m.group(1).strip()
    m = re.search(r'配偶长相[^>]*>：([^<]+)', html)
    if m:
        marriage["配偶长相"] = m.group(1).strip()[:200]

    if marriage:
        data["marriage"] = marriage

    # 财运
    caiyun = {}
    m = re.search(r'求财途径建议：([^<]+)', html)
    if m:
        caiyun["求财途径"] = m.group(1).strip()[:200]
    m = re.search(r'财运分析：[^>]*>身弱[^<]+', html)
    if m:
        caiyun["财运总评"] = m.group(0).strip()[:300]
    m = re.search(r'所欠阴债[^>]*>[^>]+>(\d+贯)', html)
    if m:
        caiyun["阴债"] = m.group(1)
    if caiyun:
        data["caiyun"] = caiyun

    # 2026开运建议
    kaiyun = {}
    m = re.search(r'2026[^<]*躲星[^<]*时间：([^<]+)<', html)
    if m:
        kaiyun["躲星时间"] = m.group(1).strip()
    m = re.search(r'2026[^<]*生肖[^<]*破太岁[^<]*（[^）]+）', html)
    if m:
        kaiyun["生肖提醒"] = m.group(1).strip()
    if kaiyun:
        data["kaiyun_2026"] = kaiyun

    return data


def cmd_fetch():
    """fortune.py fetch <year> <month> <day> <hour> <minute> <gender>"""
    args = sys.argv[2:]
    if len(args) < 6:
        print("Usage: fortune.py fetch <year> <month> <day> <hour> <minute> <gender>")
        sys.exit(1)

    year, month, day, hour, minute, gender = args[:6]
    data = fetch_bazi(year, month, day, hour, minute, gender)

    user = {
        "birth": {
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "hour": int(hour),
            "minute": int(minute),
            "gender": gender
        },
        "bazi": data,
        "fetched_at": datetime.now(TZ).isoformat()
    }
    save_user(user)
    print(json.dumps(user, ensure_ascii=False, indent=2))


def cmd_view():
    """fortune.py view - 显示已保存的信息摘要"""
    user = load_user()
    if not user:
        print("未找到八字信息，请先输入生日信息开始算命。")
        sys.exit(1)

    birth = user["birth"]
    bazi = user.get("bazi", {})
    bazi_summary = bazi.get("bazi", {})
    mingge = bazi.get("mingge", "")
    wangshuai = bazi.get("wangshuai", "")
    xiyong = bazi.get("xiyong", "")

    gender_display = "男" if birth["gender"] == "男" else "女"
    lines = [
        f"性别：{gender_display}",
        f"公历：{birth['year']}年{birth['month']}月{birth['day']}日{birth['hour']}点{birth['minute']}分",
        f"农历：{bazi.get('lunar', {}).get('year', '?')}年{bazi.get('lunar', {}).get('month', '?')}月{bazi.get('lunar', {}).get('day', '?')}日{bazi.get('lunar', {}).get('hour', '')}时",
        f"生辰（八字）：{' '.join(bazi_summary.values()) if isinstance(bazi_summary, dict) else bazi_summary}",
        f"五行：{bazi.get('wuxing', '')}",
        f"命格：{mingge}" if mingge else "",
        f"旺衰：{wangshuai}" if wangshuai else "",
        f"喜用：{xiyong}" if xiyong else "",
        f"星座：{bazi.get('constellation', '')}",
        f"称骨：{bazi.get('chengguxiang', '')}",
        f"命卦：{bazi.get('minggua', '')}",
        f"空亡：{bazi.get('kongwang', '')}",
    ]
    print("\n".join(line for line in lines if line))


def cmd_status():
    """fortune.py status - 检查是否已有保存的八字"""
    user = load_user()
    if user:
        birth = user["birth"]
        bazi = user.get("bazi", {}).get("bazi", {})
        gender_display = "男" if birth["gender"] == "男" else "女"
        if isinstance(bazi, dict):
            bazi_str = " ".join(bazi.values())
        else:
            bazi_str = str(bazi)
        print(f"EXISTS:{gender_display}:{birth['year']}年{birth['month']}月{birth['day']}日:{bazi_str}")
    else:
        print("NOT_FOUND")


def cmd_clear():
    """fortune.py clear - 删除保存的信息"""
    if os.path.exists(USER_FILE):
        os.remove(USER_FILE)
        print("已清除八字信息。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fortune.py <fetch|view|status|clear>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "fetch":
        cmd_fetch()
    elif cmd == "view":
        cmd_view()
    elif cmd == "status":
        cmd_status()
    elif cmd == "clear":
        cmd_clear()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
