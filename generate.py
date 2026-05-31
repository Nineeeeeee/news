#!/usr/bin/env python3
"""Extract matched news from TrendRadar DB and generate daily HTML page."""

import sqlite3
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

REPO_DIR = Path("/home/fengxuwen/news")
DB_DIR = Path("/home/fengxuwen/trendradar/output/news")
KEYWORDS_FILE = Path("/home/fengxuwen/trendradar/config/frequency_words.txt")
HTML_DIR = Path("/home/fengxuwen/trendradar/output/html")

# Platform display names
PLATFORM_NAMES = {
    "toutiao": "今日头条", "baidu": "百度热搜", "weibo": "微博",
    "zhihu": "知乎", "douyin": "抖音", "bilibili-hot-search": "B站热搜",
    "wallstreetcn-hot": "华尔街见闻", "cls-hot": "财联社",
    "thepaper": "澎湃新闻", "ifeng": "凤凰网", "tieba": "贴吧",
}

def load_keywords():
    if not KEYWORDS_FILE.exists():
        return []
    with open(KEYWORDS_FILE) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def get_today_matches():
    today = date.today().isoformat()  # 2026-05-31
    db_path = DB_DIR / f"{today}.db"
    if not db_path.exists():
        print(f"No DB for {today}")
        return []
    
    keywords = load_keywords()
    db = sqlite3.connect(str(db_path))
    cur = db.cursor()
    
    # Get all news items for today, with platform names
    rows = cur.execute("""
        SELECT p.name, p.id, n.title, n.rank, n.url, n.first_crawl_time, n.last_crawl_time, n.crawl_count
        FROM news_items n
        JOIN platforms p ON n.platform_id = p.id
        ORDER BY n.rank
    """).fetchall()
    
    db.close()
    
    # Match against keywords
    matched = []
    for row in rows:
        name, pid, title, rank, url, first_time, last_time, count = row
        matched_kw = None
        for kw in keywords:
            if kw.lower() in title.lower():
                matched_kw = kw
                break
        if matched_kw:
            matched.append({
                "platform": name,
                "platform_id": pid,
                "title": title,
                "rank": rank,
                "url": url,
                "first_time": first_time,
                "last_time": last_time,
                "crawl_count": count,
                "keyword": matched_kw,
            })
    
    return matched

def generate_day_page(matches, target_date):
    """Generate HTML for a single day's news, with date navigation."""
    date_str = target_date.isoformat()
    
    items_html = ""
    if not matches:
        items_html = '<div class="empty">今天还没有匹配的新闻，等 TrendRadar 抓取后会出现在这里</div>'
    else:
        # Group by platform
        by_platform = {}
        for m in matches:
            plat = m["platform"]
            if plat not in by_platform:
                by_platform[plat] = []
            by_platform[plat].append(m)
        
        for plat, items in sorted(by_platform.items()):
            items_html += f'<div class="platform-group">\n'
            items_html += f'<h2 class="platform-name">{plat} ({len(items)}条)</h2>\n'
            for item in sorted(items, key=lambda x: x["rank"]):
                title = item["title"]
                url = item.get("url", "")
                rank = item["rank"]
                kw = item["keyword"]
                first = item.get("first_time", "")
                if first:
                    # Time format: "HH-MM" from TrendRadar DB
                    first = first.replace("-", ":")
                
                title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
                items_html += '<div class="news-item">\n'
                items_html += f'  <span class="rank">#{rank}</span>\n'
                items_html += f'  <span class="kw-tag">{kw}</span>\n'
                items_html += f'  <span class="news-title">{title_html}</span>\n'
                if first:
                    items_html += f'  <span class="time">{first}</span>\n'
                items_html += '</div>\n'
            items_html += '</div>\n'
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>热点新闻 - {date_str}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0f1117; color: #c9d1d9; padding: 20px; max-width: 800px; margin: 0 auto;
}}
h1 {{
    text-align: center; font-size: 1.5em; margin-bottom: 24px;
    color: #58a6ff; padding-bottom: 12px; border-bottom: 1px solid #21262d;
}}
.back-link {{
    display: block; text-align: center; margin-bottom: 20px;
    color: #8b949e; font-size: 0.9em; text-decoration: none;
}}
.back-link:hover {{ color: #58a6ff; }}
.platform-group {{
    margin-bottom: 24px; background: #161b22; border-radius: 8px;
    padding: 16px; border: 1px solid #21262d;
}}
.platform-name {{
    font-size: 1.1em; color: #58a6ff; margin-bottom: 12px;
    padding-bottom: 8px; border-bottom: 1px solid #21262d;
}}
.news-item {{
    display: flex; align-items: baseline; gap: 8px; padding: 6px 0;
    border-bottom: 1px solid #21262d22; font-size: 0.95em; line-height: 1.5;
}}
.news-item:last-child {{ border-bottom: none; }}
.rank {{
    color: #f0883e; font-weight: bold; min-width: 28px; font-size: 0.85em;
}}
.kw-tag {{
    background: #1f6feb33; color: #58a6ff; padding: 1px 6px;
    border-radius: 4px; font-size: 0.75em; white-space: nowrap;
}}
.news-title {{ flex: 1; }}
.news-title a {{ color: #c9d1d9; text-decoration: none; }}
.news-title a:hover {{ color: #58a6ff; text-decoration: underline; }}
.time {{ color: #484f58; font-size: 0.8em; white-space: nowrap; }}
.empty {{
    text-align: center; padding: 60px 20px; color: #484f58; font-size: 1em;
}}
footer {{
    text-align: center; margin-top: 40px; padding-top: 20px;
    border-top: 1px solid #21262d; color: #30363d; font-size: 0.8em;
}}
</style>
</head>
<body>
<a href="../.." class="back-link">⬅ 返回日历</a>
<h1>{date_str} 热点新闻</h1>
{items_html}
<footer>powered by TrendRadar · auto-generated</footer>
</body>
</html>'''

def generate_index():
    """Generate the main index.html with date picker UI."""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>热点新闻日报</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0f1117; color: #c9d1d9; min-height: 100vh;
}
.header {
    background: #161b22; border-bottom: 1px solid #21262d; padding: 16px 20px;
    position: sticky; top: 0; z-index: 10;
}
.header-inner {
    max-width: 800px; margin: 0 auto; display: flex; align-items: center; gap: 16px;
    flex-wrap: wrap;
}
.header h1 {
    color: #58a6ff; font-size: 1.3em; white-space: nowrap;
}
.date-nav {
    display: flex; align-items: center; gap: 8px; flex: 1; min-width: 200px;
}
.date-nav input[type="date"] {
    background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
    padding: 6px 12px; border-radius: 6px; font-size: 0.95em; font-family: inherit;
}
.date-nav input[type="date"]:focus { outline: none; border-color: #58a6ff; }
.date-nav button {
    background: #238636; border: none; color: white; padding: 6px 14px;
    border-radius: 6px; cursor: pointer; font-size: 0.9em; font-family: inherit;
}
.date-nav button:hover { background: #2ea043; }
.date-nav .today-btn {
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
}
.date-nav .today-btn:hover { background: #30363d; }
.content {
    max-width: 800px; margin: 0 auto; padding: 20px;
}
.platform-group {
    margin-bottom: 24px; background: #161b22; border-radius: 8px;
    padding: 16px; border: 1px solid #21262d;
}
.platform-name {
    font-size: 1.1em; color: #58a6ff; margin-bottom: 12px;
    padding-bottom: 8px; border-bottom: 1px solid #21262d;
}
.news-item {
    display: flex; align-items: baseline; gap: 8px; padding: 6px 0;
    border-bottom: 1px solid #21262d22; font-size: 0.95em; line-height: 1.5;
}
.news-item:last-child { border-bottom: none; }
.rank { color: #f0883e; font-weight: bold; min-width: 28px; font-size: 0.85em; }
.kw-tag {
    background: #1f6feb33; color: #58a6ff; padding: 1px 6px;
    border-radius: 4px; font-size: 0.75em; white-space: nowrap;
}
.news-title { flex: 1; }
.news-title a { color: #c9d1d9; text-decoration: none; }
.news-title a:hover { color: #58a6ff; text-decoration: underline; }
.time { color: #484f58; font-size: 0.8em; white-space: nowrap; }
.empty {
    text-align: center; padding: 60px 20px; color: #484f58; font-size: 1.1em;
}
.empty .icon { font-size: 3em; margin-bottom: 16px; }
.loading {
    text-align: center; padding: 60px; color: #484f58;
}
footer {
    text-align: center; margin-top: 40px; padding: 20px; color: #30363d;
    font-size: 0.8em; border-top: 1px solid #21262d; max-width: 800px; margin-left: auto; margin-right: auto;
}
</style>
</head>
<body>
<div class="header">
    <div class="header-inner">
        <h1>热点新闻日报</h1>
        <div class="date-nav">
            <input type="date" id="datePicker">
            <button onclick="loadDate()">查看</button>
            <button class="today-btn" onclick="loadToday()">今天</button>
        </div>
    </div>
</div>

<div class="content" id="newsContent">
    <div class="loading">加载中...</div>
</div>

<footer>powered by TrendRadar · auto-generated</footer>

<script>
const BASE = window.location.pathname.substring(0, window.location.pathname.lastIndexOf('/') + 1);

// Set date picker to today
const today = new Date().toISOString().split("T")[0];
document.getElementById("datePicker").value = today;

function loadDate() {
    const d = document.getElementById("datePicker").value;
    if (!d) return;
    loadNews(d);
}

function loadToday() {
    document.getElementById("datePicker").value = today;
    loadNews(today);
}

async function loadNews(dateStr) {
    const content = document.getElementById("newsContent");
    content.innerHTML = '<div class="loading">加载中...</div>';
    document.getElementById("datePicker").value = dateStr;
    
    try {
        const resp = await fetch(`${BASE}${dateStr.slice(0,4)}/${dateStr.slice(5,7)}/${dateStr.slice(8,10)}/index.html?_=${Date.now()}`);
        if (resp.ok) {
            const html = await resp.text();
            // Extract body content only
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const bodyContent = doc.querySelector("body");
            // Remove header/footer from embedded page
            const h1 = bodyContent.querySelector("h1");
            const backLink = bodyContent.querySelector(".back-link");
            const footer = bodyContent.querySelector("footer");
            if (backLink) backLink.remove();
            if (footer) footer.remove();
            // Update h1 to just show date
            if (h1) h1.style.marginTop = "0";
            
            content.innerHTML = bodyContent.innerHTML;
        } else {
            content.innerHTML = `<div class="empty"><div class="icon">📭</div>${dateStr} 暂无数据</div>`;
        }
    } catch (e) {
        content.innerHTML = `<div class="empty"><div class="icon">📭</div>${dateStr} 暂无数据</div>`;
    }
}

// Load today on page load
loadNews(today);
</script>
</body>
</html>'''

def main():
    today = date.today()
    matches = get_today_matches()
    
    # Create directory for today
    date_dir = REPO_DIR / str(today.year) / f"{today.month:02d}" / f"{today.day:02d}"
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate day page
    day_html = generate_day_page(matches, today)
    (date_dir / "index.html").write_text(day_html, encoding="utf-8")
    print(f"Generated: {date_dir}/index.html ({len(matches)} news items)")
    
    # Generate main index.html
    index_html = generate_index()
    (REPO_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"Generated: {REPO_DIR}/index.html")
    
    # Git commit and push
    os.chdir(REPO_DIR)
    os.system("git add -A")
    commit_msg = f"Update {today.isoformat()} - {len(matches)} news items"
    ret = os.system(f'git commit -m "{commit_msg}" 2>&1')
    if ret == 0:
        os.system("git push origin main 2>&1")
        print("Pushed to GitHub")
    else:
        print("No changes to commit")

if __name__ == "__main__":
    main()
