#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最新AIニュース自動収集・Discord通知ボット

- Tavily API で AI 関連ニュースを3件取得し、要約を Markdown に保存
- Discord Webhook で要約を通知（2000文字制限対応）
- 環境変数から API キーと Webhook URL を読み込み（python-dotenv）
- タイムアウト・レートリミット・クオータ超過時のリトライロジックあり
"""

import os
import time
import json
import logging
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv

# ----------------------------
# 設定・定数
# ----------------------------
load_dotenv()  # .env ファイルから環境変数を読み込む

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not TAVILY_API_KEY or not DISCORD_WEBHOOK_URL:
    raise EnvironmentError(
        "TAVILY_API_KEY と DISCORD_WEBHOOK_URL を .env ファイルに設定してください"
    )

TAVILY_ENDPOINT = "https://api.tavily.com/search"
MAX_DISCORD_LEN = 2000          # Discord の実際の制限
SAFE_LEN = 1900                 # 余裕を持たせた切り詰め長さ
REQUEST_TIMEOUT = 10            # seconds
MAX_RETRY = 3                   # ネットワークエラー時のリトライ回数
BACKOFF_FACTOR = 2              # 指数バックオフの基数

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ----------------------------
# Tavily API ラッパー
# ----------------------------
def _tavily_request(payload: Dict) -> Dict:
    """Tavily API へPOSTし、JSONレスポンスを返す。リトライ・例外処理内蔵."""
    headers = {"Content-Type": "application/json"}
    payload["api_key"] = TAVILY_API_KEY

    attempt = 0
    while True:
        try:
            resp = requests.post(
                TAVILY_ENDPOINT,
                headers=headers,
                data=json.dumps(payload),
                timeout=REQUEST_TIMEOUT,
            )
            # レートリミット（429）またはクオータ超過（429 に quota 含む）の場合
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "1"))
                logger.warning(
                    f"Rate limited. Waiting {retry_after}s before retry (attempt {attempt+1}/{MAX_RETRY})"
                )
                time.sleep(retry_after)
                attempt += 1
                if attempt > MAX_RETRY:
                    resp.raise_for_status()
                continue

            # その他のHTTPエラー
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            logger.warning(
                f"Timeout on Tavily request (attempt {attempt+1}/{MAX_RETRY})"
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"RequestException: {e} (attempt {attempt+1}/{MAX_RETRY})")

        attempt += 1
        if attempt > MAX_RETRY:
            logger.error("Max retries exceeded for Tavily request")
            raise
        # 指数バックオフ
        sleep_sec = BACKOFF_FACTOR ** attempt
        logger.info(f"Retrying in {sleep_sec}s...")
        time.sleep(sleep_sec)


def fetch_ai_news(query: str = "AI技術 最新ニュース 2026年3月", max_results: int = 3) -> List[Dict]:
    """Tavily でニュースを検索し、結果のリストを返す."""
    payload = {
        "query": query,
        "max_results": max_results,
        "include_answer": True,   # answer フィールドがあれば利用
        "include_raw_content": False,
    }
    data = _tavily_request(payload)
    # Tavily のレスポンス構造: { "answer": str, "results": [ { "title", "url", "content", ... } ], ... }
    results = data.get("results", [])
    answer = data.get("answer")
    # answer がある場合はそれを最初の要素として扱う（フォールバックとして利用）
    if answer:
        results.insert(
            0,
            {
                "title": "AI ニューサマリー (Tavily answer)",
                "url": "",
                "content": answer,
                "score": 1.0,
            },
        )
    return results[:max_results]


# ----------------------------
# Markdown 生成
# ----------------------------
def build_markdown(news_items: List[Dict]) -> str:
    """ニュース項目から Markdown テキストを作成."""
    lines = ["# 最新AIニュース (自動取得)", ""]
    for i, item in enumerate(news_items, start=1):
        title = item.get("title", "(タイトルなし)")
        url = item.get("url", "")
        snippet = item.get("content", "").strip()
        # 改行をスペースに置換し、過長を防ぐ
        snippet = " ".join(snippet.split())
        lines.append(f"## {i}. {title}")
        if url:
            lines.append(f"**出典**: {url}")
        lines.append(f"**要約**: {snippet}")
        lines.append("")  # 空行
    return "\n".join(lines)


def save_to_file(markdown_text: str, path: str = "daily_news.md") -> None:
    """Markdown テキストをファイルに書き込む."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    logger.info(f"Markdown saved to {path}")


# ----------------------------
# Discord 通知
# ----------------------------
def _split_message(text: str, limit: int = MAX_DISCORD_LEN) -> List[str]:
    """limit 文字ごとに分割し、リストで返す（空文字列は除外）."""
    if not text:
        return []
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def send_to_discord(markdown_text: str) -> None:
    """Discord Webhook へメッセージを送信。2000文字制限を超える場合は分割送信."""
    # SAFE_LEN で切り詰め（末尾に「…」を付加）
    if len(markdown_text) > SAFE_LEN:
        summary = markdown_text[:SAFE_LEN] + "…"
    else:
        summary = markdown_text

    chunks = _split_message(summary, limit=MAX_DISCORD_LEN)
    payload_base = {"content": ""}

    for idx, chunk in enumerate(chunks, start=1):
        payload = {**payload_base, "content": chunk}
        attempt = 0
        while True:
            try:
                resp = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "1"))
                    logger.warning(
                        f"Discord rate limited. Waiting {retry_after}s (chunk {idx})"
                    )
                    time.sleep(retry_after)
                    attempt += 1
                    if attempt > MAX_RETRY:
                        resp.raise_for_status()
                    continue
                resp.raise_for_status()
                logger.info(f"Discord message sent (chunk {idx}/{len(chunks)})")
                break
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                logger.warning(
                    f"Discord send error: {e} (chunk {idx}, attempt {attempt+1}/{MAX_RETRY})"
                )
                attempt += 1
                if attempt > MAX_RETRY:
                    logger.error(
                        f"Failed to send Discord message after {MAX_RETRY} retries (chunk {idx})"
                    )
                    raise
                sleep_sec = BACKOFF_FACTOR ** attempt
                logger.info(f"Retrying Discord send in {sleep_sec}s...")
                time.sleep(sleep_sec)


# ----------------------------
# メイン処理
# ----------------------------
def main() -> None:
    logger.info("Starting AI news bot...")
    try:
        news_items = fetch_ai_news()
        if not news_items:
            logger.warning("No news items fetched from Tavily.")
            return

        md_text = build_markdown(news_items)
        save_to_file(md_text, "daily_news.md")
        send_to_discord(md_text)
        logger.info("Bot execution completed successfully.")
    except Exception as exc:
        logger.exception("Unexpected error occurred")
        # 致命的エラーでもDiscordに通知したい場合はこちらで送信可
        error_msg = f":x: ボット実行中にエラーが発生しました: {exc}"
        try:
            send_to_discord(error_msg)
        except Exception:
            pass  # 通知失敗はログのみに留める


if __name__ == "__main__":
    main()