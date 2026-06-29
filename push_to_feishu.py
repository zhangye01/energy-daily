#!/usr/bin/env python3
"""将每日简报推送到飞书群"""
import json, sys, re, urllib.request
from datetime import datetime, timezone, timedelta

WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/ca9777ed-780a-4815-ae9e-082dfe85ef1a"

def parse_report(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if date_match:
        date_str = f"{date_match.group(1)}年{date_match.group(2)}月{date_match.group(3)}日"
    else:
        date_str = "今日"

    sections = {}
    current_cat = None
    total = 0

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        for cat in ["政策法规", "市场动态", "新能源发展", "行业企业", "国际能源"]:
            if f"## {cat}" == line:
                current_cat = cat
                sections[current_cat] = []
                break
        else:
            if current_cat and line.startswith("- **"):
                total += 1
                clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                clean = clean.replace("- **", "• **").replace("** —", "**\n  ")
                clean = re.sub(r'（来源：[^）]*）', '', clean)
                sections[current_cat].append(clean)

    if "## 今日要闻" in text:
        highlights = []
        in_highlights = False
        for line in text.split("\n"):
            if "## 今日要闻" in line:
                in_highlights = True
                continue
            if in_highlights and line.startswith("##"):
                break
            if in_highlights and line.strip().startswith("- **"):
                clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line.strip())
                clean = clean.replace("- **", "• **")
                clean = re.sub(r'（来源：[^）]*）', '', clean)
                highlights.append(clean)
        sections["_highlights"] = highlights

    return date_str, sections, total

def build_card(date_str, sections, total):
    elements = []

    highlights = sections.pop("_highlights", [])
    if highlights:
        htext = "\n".join(highlights[:5])
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🔥 今日要闻**\n{htext}"}
        })
        elements.append({"tag": "hr"})

    cat_order = ["政策法规", "市场动态", "新能源发展", "行业企业", "国际能源"]
    cat_emoji = {"政策法规": "📋", "市场动态": "📈", "新能源发展": "🌱", "行业企业": "🏭", "国际能源": "🌍"}
    stats = []

    for cat in cat_order:
        items = sections.get(cat, [])
        if not items:
            continue
        stats.append(f"{cat}：{len(items)}条")
        text = f"**{cat_emoji[cat]} {cat}**\n" + "\n".join(items)
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": text}
        })
        elements.append({"tag": "hr"})

    stat_line = "  |  ".join(stats)
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"共收录 {total} 条动态 | {stat_line}\nWorkBuddy 自动生成 | 数据来源：公开信息"}]
    })
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📂 查看历史合集"},
            "url": "https://zhangye01.github.io/energy-daily/",
            "type": "default"
        }]
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"能源电力市场每日动态 | {date_str}"},
                "template": "green"
            },
            "elements": elements
        }
    }

def send(card):
    data = json.dumps(card, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={
        "Content-Type": "application/json"
    })
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode())
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: push_to_feishu.py <report.md>")
        sys.exit(1)

    path = sys.argv[1]
    date_str, sections, total = parse_report(path)
    card = build_card(date_str, sections, total)
    result = send(card)

    if result.get("code") == 0:
        print(f"已推送到飞书群 | {date_str} | {total}条动态")
    else:
        print(f"推送失败: {result}")
        sys.exit(1)
