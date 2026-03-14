# コンサルティング報告書：最新AIニュース自動収集・Discord通知ボット  
**作成日**：2025年9月16日  
**対象フォルダ**：`output/news_bot`  

---

## 1. サマリー  
本プロジェクトは、2026年3月現在の最新AI技術・ツールに関するニュースを **Tavily API** で自動取得し、要約して Markdown ファイル (`daily_news.md`) に保存、さらに Discord Webhook を使って要約を通知する Python ボットを構築するものです。  

- **主な機能**  
  1. Tavily から AI 関連ニュースを 3 件取得（無料プランでも日次実行に十分）  
  2. 取得結果を簡易要約（先頭 200 文字＋リンク）  
  3. `daily_news.md` に日付見出し付きで追記保存  
  4. Discord Webhook へ POST（文字数 2000 制限を超えないよう自動トリム）  
  5. 環境変数（`.env`) から Webhook URL を安全に読み込み  

- **想定利用シーン**  
  - 個人開発者や小規模チームが毎朝の AI 動向を把握するための軽量情報収集ツール  
  - Discord チャンネルへの自動通知により、情報共有の手間を削減  

---

## 2. 技術構成案  

| コンポーネント | 技術・ライブラリ | 役割 |
|----------------|------------------|------|
| **言語** | Python 3.11+ | メイン実装 |
| **HTTP クライアント** | `requests` | Tavily API および Discord Webhook へのリクエスト |
| **環境変数管理** | `python-dotenv` | `.env` から `DISCORD_WEBHOOK_URL` を読み込み |
| **日付・ファイル操作** | 標準ライブラリ (`datetime`, `pathlib`) | `daily_news.md` の生成・追記 |
| **例外ハンドリング** | `try/except` + カスタムログ | ネットワークエラーや API 制限時の graceful デグレード |
| **テストフレームワーク** | `pytest`（開発時） | 関数単位のユニットテスト |
| **ロギング** | 標準 `logging`（ローテートは `logging.handlers.RotatingFileHandler`） | 実行ログとエラー記録 |
| **キャッシュ（オプション）** | `diskcache`（将