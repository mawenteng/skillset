# -*- coding: utf-8 -*-
"""
ProMED 通过「点击列表项 → 右侧详情」抓取正文（不跳转新页面）。

交互逻辑（你补充的）：
- 第一次点击某条标题：右侧出现摘要；
- 点击「阅读全文」：右侧显示全文；
- 再点击其它列表项标题：右侧直接显示全文。

本脚本：登录 → 首页 → 只抓**当天发布**的**前 2 条** → 逐条点击标题 → 若出现「阅读全文」则点击 →
从右侧内容区取正文并保存到同一 txt。

依赖：pip install playwright python-dotenv && playwright install chromium
"""
from datetime import datetime, timedelta
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from playwright.sync_api import sync_playwright

BASE = "https://www.promedmail.org/"
LOGIN_PATH = "/auth/login"
# 保存到工作区目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "KnowledgeBase" / "data" / "crawled" / "promedmail"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(date_str):
    """解析表格日期，如 'Fri Jan 30 2026' -> date。失败返回 None。"""
    s = (date_str or "").strip()
    for fmt in ("%a %b %d %Y", "%A %b %d %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def get_credentials():
    user = os.environ.get("PROMED_USER", "").strip()
    password = os.environ.get("PROMED_PASSWORD", "").strip()
    if not user or not password:
        print("Error: PROMED_USER and PROMED_PASSWORD must be set (in .env).")
        raise SystemExit(1)
    return user, password


def login(page, user, password):
    login_url = BASE.rstrip("/") + LOGIN_PATH
    print("Opening login page:", login_url)
    page.goto(login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    email_sel = 'input[name="username"], input[type="email"], input[name="email"]'
    pw_sel = 'input[type="password"]'
    submit_sel = 'button[type="submit"], button:has-text("Continue"), button:has-text("Log in"), button:has-text("Sign in")'
    try:
        page.wait_for_selector(email_sel, timeout=15000)
    except Exception as e:
        print("Login: email input not found:", e)
        return False
    page.fill(email_sel, user)
    page.fill(pw_sel, password)
    page.click(submit_sel)
    try:
        page.wait_for_load_state("load", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(5000)
    if "auth.promedmail.org" in page.url or "login" in page.url.lower():
        print("Still on login page.")
        return False
    print("Login succeeded.")
    return True


def goto_homepage(page):
    if BASE.rstrip("/") not in page.url or "/auth" in page.url:
        print("Navigating to homepage:", BASE)
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    return page.url


def get_list_rows(page):
    """获取表格行（跳过表头），每行可点击第二列（标题）。"""
    rows = page.locator("table tbody tr, table tr").all()
    result = []
    for tr in rows:
        try:
            cell_loc = tr.locator("td, th, [role='cell']")
            if cell_loc.count() < 2:
                continue
            date_text = cell_loc.nth(0).inner_text().strip()
            title = cell_loc.nth(1).inner_text().strip()
            if date_text.upper() == "DATE" and title.upper() == "TITLE":
                continue
            result.append({"date": date_text, "title": title, "row": tr})
        except Exception:
            continue
    return result


# 右侧「阅读全文」按钮可能文案（中/英）
READ_FULL_TEXTS = [
    "阅读全文",
    "Read full text",
    "Read full article",
    "Full text",
    "Read more",
    "View full",
]


def click_read_full_if_present(page):
    """若右侧出现「阅读全文」类按钮则点击，并等待内容更新。"""
    for text in READ_FULL_TEXTS:
        try:
            btn = page.get_by_role("button", name=text).or_(page.get_by_role("link", name=text))
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    # 备用：按可见文本匹配
    try:
        for text in READ_FULL_TEXTS:
            loc = page.locator(f"button:has-text('{text}'), a:has-text('{text}')").first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                page.wait_for_timeout(2500)
                return True
    except Exception:
        pass
    return False


def get_right_panel_text(page):
    """
    从右侧详情区取正文。排除左侧列表（含 "Latest Posts on ProMED" 的区块），
    取右侧摘要/正文容器。
    """
    # 1) 先找「阅读全文」按钮所在容器，该容器通常是右侧详情
    try:
        text = page.evaluate("""() => {
            const btnTexts = ['Read full text', '阅读全文', 'Read more', 'Full text'];
            for (const btnText of btnTexts) {
                const nodes = document.querySelectorAll('button, a');
                for (const n of nodes) {
                    if ((n.innerText || '').trim().toLowerCase().includes(btnText.toLowerCase())) {
                        let p = n.closest('article') || n.closest('[class*="content"]') || n.closest('section') || n.parentElement;
                        for (let i = 0; i < 15 && p; i++) {
                            const t = (p.innerText || '').trim();
                            if (t.length > 200 && !t.includes('Latest Posts on ProMED')) return t;
                            p = p.parentElement;
                        }
                    }
                }
            }
            return '';
        }""")
        if text and len(text) > 200:
            return text
    except Exception:
        pass
    # 2) 语义化容器
    for sel in ["article", "[role='main']", "main", "[class*='prose']"]:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                text = el.inner_text()
                if text and len(text.strip()) > 100 and "Latest Posts on ProMED" not in text:
                    return text.strip()
        except Exception:
            continue
    # 3) JS：取最大文本块且不含左侧列表
    try:
        text = page.evaluate("""() => {
            const skip = (el) => (el.innerText || '').includes('Latest Posts on ProMED');
            let best = { len: 0, text: '' };
            const walk = (el) => {
                if (!el || el.tagName === 'SCRIPT' || el.tagName === 'STYLE') return;
                if (skip(el)) return;
                const t = (el.innerText || '').trim();
                if (t.length > 300 && t.length > best.len && !el.querySelector('table')) {
                    best = { len: t.length, text: t };
                }
                for (const c of el.children || []) walk(c);
            };
            walk(document.body);
            return best.text;
        }""")
        if text and len(text) > 100 and "Latest Posts on ProMED" not in text:
            return text
    except Exception:
        pass
    return ""


def main(days=1, limit=2):
    user, password = get_credentials()
    headless = os.environ.get("HEADLESS", "1").strip().lower() not in ("0", "false", "no")
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=days-1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Chrome/120.0.0.0) Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            if not login(page, user, password):
                print("Login failed. Exiting.")
                return
            goto_homepage(page)

            all_rows = get_list_rows(page)
            if not all_rows:
                print("No list rows found.")
                return
            # 只保留最近 N 天发布的，且只抓前 limit 条
            rows = []
            for r in all_rows:
                row_date = parse_date(r["date"])
                if row_date and row_date >= cutoff_date:
                    rows.append(r)
            rows = rows[:limit]
            if not rows:
                print(f"No items published in the last {days} days. List has {len(all_rows)} items total.")
                return
            total = len(rows)
            print(f"Last {days} days: fetching first {total} items only.")

            results = []
            read_full_clicked_once = False  # 第一次需要点「阅读全文」，之后右侧可能直接全文

            for i, item in enumerate(rows):
                date_text = item["date"]
                title = item["title"]
                row = item["row"]
                print(f"[{i+1}/{total}] {title[:50]}...")

                try:
                    # 点击标题（第二列）
                    cell1 = row.locator("td, th, [role='cell']").nth(1)
                    cell1.click()
                    page.wait_for_timeout(2200)

                    # 第一次或当次只出现摘要时：点「阅读全文」
                    if not read_full_clicked_once:
                        if click_read_full_if_present(page):
                            read_full_clicked_once = True
                    else:
                        # 后续列表项：若仍看到「阅读全文」也点一下（有时会直接全文）
                        click_read_full_if_present(page)

                    body = get_right_panel_text(page)
                    if body:
                        results.append({
                            "date": date_text,
                            "title": title,
                            "body": body,
                        })
                    else:
                        results.append({"date": date_text, "title": title, "body": "[No content captured]"})
                except Exception as e:
                    print(f"  Error: {e}")
                    results.append({"date": date_text, "title": title, "body": f"[Error: {e}]"})

            if results:
                sep = "\n" + "=" * 80 + "\n"
                today = datetime.now().date().isoformat().replace("-", "")
                out_path = OUT_DIR / f"promed_by_click_{today}.txt"
                with out_path.open("w", encoding="utf-8") as f:
                    for r in results:
                        f.write(f"Title: {r['title']}\nDate: {r['date']}\n\n{r['body']}\n{sep}")
                print(f"Saved {len(results)} items to {out_path}")
        finally:
            browser.close()

    print("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抓取ProMED报告')
    parser.add_argument('--days', type=int, default=1, help='抓取最近多少天的报告')
    parser.add_argument('--limit', type=int, default=2, help='抓取前多少条报告')
    args = parser.parse_args()
    main(days=args.days, limit=args.limit)
