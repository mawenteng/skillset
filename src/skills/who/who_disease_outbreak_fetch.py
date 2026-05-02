# -*- coding: utf-8 -*-
"""
WHO Disease Outbreak News - 使用 Playwright 抓取列表前 3 条的具体内容并保存为 txt。

流程：打开列表页 → 等待列表加载 → 取前 3 项 → 逐条进入详情页 → 提取正文 → 保存到 txt。

依赖：pip install playwright && playwright install chromium
"""
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://www.who.int/emergencies/disease-outbreak-news"
# 保存到工作区目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "KnowledgeBase" / "data" / "crawled" / "who"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(date_str):
    """解析日期字符串为日期对象"""
    if not date_str:
        return None
    # 尝试不同的日期格式
    formats = ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def get_list_items(page, limit=3):
    """等待列表加载，返回前 limit 条：{title, date, href, date_obj}"""
    # 等待 Kendo 渲染出列表项
    page.locator("a.sf-list-vertical__item").first.wait_for(state="visible", timeout=20000)
    page.wait_for_timeout(1500)

    items = page.locator("a.sf-list-vertical__item").all()
    result = []
    for i, item in enumerate(items):
        if i >= limit:
            break
        try:
            href = item.get_attribute("href") or ""
            if href and not href.startswith("http"):
                href = "https://www.who.int" + (href if href.startswith("/") else "/" + href)
            title_el = item.locator(".sf-list-vertical__title")
            date_el = item.locator(".sf-list-vertical__date")
            title = title_el.inner_text().strip() if title_el.count() > 0 else ""
            date_text = date_el.inner_text().strip() if date_el.count() > 0 else ""
            date_obj = parse_date(date_text)
            result.append({"title": title, "date": date_text, "href": href, "date_obj": date_obj})
        except Exception as e:
            print(f"  Parse item {i+1} error: {e}")
    return result


def get_article_content(page):
    """从 WHO 详情页提取正文。"""
    # 常见正文容器
    for sel in [
        "main .sf-content-block",
        "main article",
        "main [class*='content-block']",
        "article .sf-content-block",
        "#content .sf-content-block",
        "main",
        "article",
    ]:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                text = el.inner_text().strip()
                if text and len(text) > 200:
                    # 排除导航等
                    if "Health Topics" not in text[:500] or len(text) > 1500:
                        return text
        except Exception:
            continue

    # JS 取最大文本块
    try:
        text = page.evaluate("""() => {
            const skip = (el) => {
                const t = (el.innerText || '').slice(0, 300);
                return t.includes('Health Topics') && t.includes('Countries');
            };
            let best = { len: 0, text: '' };
            const walk = (el) => {
                if (!el || ['SCRIPT','STYLE'].includes(el.tagName)) return;
                if (skip(el)) return;
                const t = (el.innerText || '').trim();
                if (t.length > 400 && t.length > best.len && !el.querySelector('nav')) {
                    best = { len: t.length, text: t };
                }
                for (const c of el.children || []) walk(c);
            };
            walk(document.body);
            return best.text;
        }""")
        if text and len(text) > 200:
            return text
    except Exception:
        pass
    return ""


def main(days=30, limit=None):
    headless = os.environ.get("HEADLESS", "1").strip().lower() not in ("0", "false", "no")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Chrome/120.0.0.0) Safari/537.36",
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            print("Opening:", URL)
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print("Retrying with wait_until=commit...")
                page.goto(URL, wait_until="commit", timeout=45000)
            page.wait_for_timeout(5000)

            items = get_list_items(page)
            if not items:
                print("No list items found.")
                return

            # 按天数过滤
            cutoff_date = datetime.now().date() - timedelta(days=days-1)
            filtered_items = []
            for item in items:
                if item.get("date_obj") and item["date_obj"] >= cutoff_date:
                    filtered_items.append(item)
            
            # 如果指定了 limit，则进一步限制数量
            if limit:
                filtered_items = filtered_items[:limit]

            print(f"Found {len(filtered_items)} items in the last {days} days. Fetching detail content...")
            results = []
            items = filtered_items

            for i, item in enumerate(items):
                title = item["title"]
                date_text = item["date"]
                href = item["href"]
                print(f"  [{i+1}/{len(items)}] {title[:60]}...")

                if not href or "item/" not in href:
                    results.append({
                        "title": title,
                        "date": date_text,
                        "href": href,
                        "body": "[No valid detail URL]",
                    })
                    continue

                try:
                    page.goto(href, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                    body = get_article_content(page)
                    results.append({
                        "title": title,
                        "date": date_text,
                        "href": href,
                        "body": body or "[Content not captured]",
                    })
                except Exception as e:
                    print(f"    Error: {e}")
                    results.append({
                        "title": title,
                        "date": date_text,
                        "href": href,
                        "body": f"[Error: {e}]",
                    })

            # 保存到 txt
            today = datetime.now().strftime("%Y%m%d")
            out_path = OUT_DIR / f"who_disease_outbreak_{today}.txt"
            sep = "\n" + "=" * 80 + "\n"
            with out_path.open("w", encoding="utf-8") as f:
                for r in results:
                    f.write(f"Title: {r['title']}\n")
                    f.write(f"Date: {r['date']}\n")
                    f.write(f"URL: {r['href']}\n\n")
                    f.write(f"{r['body']}\n{sep}")
            print(f"Saved to {out_path}")
        finally:
            browser.close()

    print("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抓取WHO疾病暴发新闻')
    parser.add_argument('--days', type=int, default=30, help='抓取最近多少天的新闻')
    parser.add_argument('--limit', type=int, default=None, help='抓取前多少条新闻（可选）')
    args = parser.parse_args()
    main(days=args.days, limit=args.limit)
