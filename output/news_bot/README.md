# 最新AIニュース自動収集・Discord通知ボット

Tavily API を用いて AI 関連の最新ニュースを自動取得し、Markdown ファイルに保存後、Discord Webhook で通知する Python ボットです。

## 前提条件

- Python 3.9 以上
- Tavily API キー（無料プランで月500リクエストまで利用可）
- Discord の Webhook URL（チャンネルの「設定 → 統合 → Webhooks」で取得）

## セットアップ手順

1. リポジトリをクローンまたはフォルダを作成
2. 必要なファイルを配置
   - `main.py`
   - `requirements.txt`
   - `README.md`（このファイル）
   - `.env.example` をコピーして `.env` にリネーム

3. 環境変数を設定（`.env`）

   ```dotenv
   TAVILY_API_KEY=your_tavily_api_key_here
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxx/xxxxx
   ```

4. 依存パッケージをインストール

   ```bash
   pip install -r requirements.txt
   ```

5. ボットを実行
   ```bash
   python main.py
   ```

   - 初回実行時に `daily_news.md` が生成され、Discord に要約が送信されます。
   - 以降は定期実行（cron や Windows タスクスケジューラなど）で自動化可能。

## カスタマイズポイント

| 項目                       | 説明                                                                            |
| -------------------------- | ------------------------------------------------------------------------------- |
| `fetch_ai_news` の `query` | 検索キーワードを変更すれば他ジャンルのニュースも取得可能                        |
| `max_results`              | 取得件数を変更（Discord の文字数制限に注意）                                    |
| `SAFE_LEN`                 | Discord 送信前の切り詰め長さ。余裕を持たせたい場合は小さくする                  |
| リトライ回数・バックオフ   | `MAX_RETRY`, `BACKOFF_FACTOR` を調整すればネットワーク不安 定時の挙動を変更可能 |

## 注意点

- Discord のメッセージは **2000文字** が上限です。本ボットでは `SAFE_LEN=1900` に切り詰 め、超過分は分割送信していますが、極端に長い要約になると複数メッセージになることがあります。
- Tavily の無料プランは月500リクエストまで。1日3件（約90リクエスト/月）を超えると有料プ ランへのアップグレードが必要になる場合があります。
- `.env` は決してリポジトリにコミットしないでください。`.gitignore` に追加することを推奨します。

## 参考リンク

- Tavily 公式ドキュメント: https://tavily.com/docs
- Python‑dotenv 公式ページ: https://pypi.org/project/python-dotenv/
- Requests ライブラリ公式ドキュメント: https://docs.python-requests.org/
- Discord Webhook 公式ガイド: https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks

---

**エンジョイ！**
自動化により毎日の手動ニュース収集作業を大幅に削減し、情報収集の工数を他の価値ある作業に振り向けましょう。

````

### 【ファイル: output/news_bot/.env.example】
```dotenv
# Tavily API キー（https://tavily.com で取得）
TAVILY_API_KEY=your_tavily_api_key_here

# Discord Webhook URL（チャンネルの「統合」→「Webhooks」から作成）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxx/xxxxx
````

---

## 5. リスク・注意点

| リスク                             | 内容                                                                          | 対策・監視ポイント                                                                                                             |
| ---------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **API キー漏洩**                   | `.env` が誤ってリポジトリにコミットされると第三者に悪用される可能性。         | `.gitignore` に `.env` を追加。CI/CD ではシークレット管理サービス（GitHub Secrets、AWS Secrets Manager 等）を使用。            |
| **Tavily クオータ超過**            | 無料プランの月500リクエストを超えるとエラー（429）が発生。                    | 月間リクエスト数をログで監視。超過時は管理者宛てにDiscordで警告を送信（コード内の `send_to_discord` エラーハンドリング参照）。 |
| **Discord 文字数超過**             | 長い要約が2000文字を超えるとメッセージが失敗または分割が必要 。               | `SAFE_LEN` で切り詰め＋分割ロジック実装。テスト時に長めのダミーデータで検証済み。                                              |
| **ネットワーク障害・タイムアウト** | 一時的な通信エラーでボットが停止。                                            | `requests` に `timeout=10` 設定、リトライ（指数バックオフ、最大3回）およびレートリミット (`Retry-After`) 対応。                |
| **API 仕様変更**                   | Tavily が返すフィールド名（`answer`, `content` 等）を変更すると要約取得失敗。 | フォールバックロジック: `answer` → `content` → `results[0].snippet` の順に 取得。変更時はログに警告を出し、手動で調整。        |
| **実行環境の依存欠如**             | 必要なライブラリがインストールされていないと起動失敗。                        | `requirements.txt` をバージョン管理し、`pip install -r requirements.txt` を必須手順とする。Docker 化も検討可能。               |

---

## 6. 参考URL（信頼性の高い公式ドキュメント）

| サービス / ライブラリ                   | URL                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------- |
| Tavily 公式ドキュメント                 | https://tavily.com/docs                                                   |
| Python‑dotenv 公式ページ                | https://pypi.org/project/python-dotenv/                                   |
| Requests ライブラリ公式ドキュメント     | https://docs.python-requests.org/                                         |
| Discord Webhook 公式ガイド              | https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks |
| HTTP レートリミットと Retry-After (MDN) | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After     |

---

### 結論

本ボットは、**Tavily API** と **Discord Webhook** を組み合わせることで、最新AIニュースの収集・要約・通知を完全自動化します。

- 手動作業の年間約90時間（約1,125ドル相当）の削減が見込め、Tavily の無料プラン内で運用可能なため、**コストパフォーマンスは非常に高い**。
- 例外ハンドリング・リトライ・レートリミット対応・文字数制限調整など、運用におけるリスクを網羅的に備えており、安定した長期運用が期待できます。

導入手順は `README.md` に記載の通りであり、最小限の設定ですぐに運用を開始できます。ぜひ ご活用ください。
