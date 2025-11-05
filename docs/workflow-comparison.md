# リハーサル記録作成ワークフロー自動化アプローチ比較検討

**作成日**: 2025-11-05
**対象**: YouTubeリンク → PDF + チャプターリスト の完全自動化

---

## ワークフロー概要

### 処理ステップ

1. **YouTube動画ダウンロード** (`ytdl-claude`)
   - 入力: YouTube URL
   - 出力: `YYYYMMDD_タイトル.mp4`, `YYYYMMDD_タイトル_yt.srt`

2. **Whisper高精度文字起こし** (`whisper-remote`)
   - 入力: `*.mp4`
   - 出力: `*_wp.srt`
   - 特記: リモートGPUサーバー接続、長時間処理（30分〜2時間）

3. **Claude AI分析 → LaTeX生成**
   - 入力: `*_yt.srt`, `*_wp.srt`
   - 出力: `*_リハーサル記録.tex`
   - 特記: AI判断が必要、完全自動化困難

4. **LuaLaTeX PDF生成** (`luatex-pdf`)
   - 入力: `*.tex`
   - 出力: `*.pdf`
   - 特記: リモートサーバーコンパイル

5. **チャプターリスト抽出** (`tex2chapters`)
   - 入力: `*.tex`
   - 出力: `*_youtube.txt`, `*_movieviewer.txt`

### 依存関係

```
YouTube URL
    ↓
[ytdl-claude] → video.mp4, video_yt.srt
    ↓
[whisper-remote] → video_wp.srt
    ↓
[Claude分析] → リハーサル記録.tex
    ↓         ↘
[luatex-pdf]  [tex2chapters]
    ↓            ↓
  *.pdf    *_youtube.txt, *_movieviewer.txt
```

---

## アプローチ1: Makefile

### 実装例

```makefile
# Makefile for rehearsal report generation
# Usage: make URL="https://youtu.be/VIDEO_ID"

# URLから生成されるファイル名（ytdl-claudeの命名規則に依存）
VIDEO_FILE = $(shell ytdl-claude "$(URL)" --dry-run 2>/dev/null | grep "Output:" | cut -d' ' -f2)
BASENAME = $(basename $(VIDEO_FILE))
YT_SRT = $(BASENAME)_yt.srt
WP_SRT = $(BASENAME)_wp.srt
TEX_FILE = $(BASENAME)_リハーサル記録.tex
PDF_FILE = $(BASENAME)_リハーサル記録.pdf
YOUTUBE_CHAPTERS = $(BASENAME)_リハーサル記録_youtube.txt
MV_CHAPTERS = $(BASENAME)_リハーサル記録_movieviewer.txt

.PHONY: all download transcribe analyze compile chapters clean

all: $(PDF_FILE) $(YOUTUBE_CHAPTERS)

# ステップ1: 動画ダウンロード
$(VIDEO_FILE) $(YT_SRT):
	ytdl-claude "$(URL)" -d

# ステップ2: Whisper文字起こし
$(WP_SRT): $(VIDEO_FILE)
	whisper-remote --demucs "$<"
	@echo "Waiting for Whisper to complete..."
	@while [ ! -f "$@" ]; do sleep 10; done

# ステップ3: Claude分析（手動介入必要）
$(TEX_FILE): $(YT_SRT) $(WP_SRT)
	@echo "ERROR: Claude AI analysis required"
	@echo "Please run: claude code"
	@echo "Then: Analyze $(YT_SRT) and $(WP_SRT) to generate $(TEX_FILE)"
	@exit 1

# ステップ4: PDF生成
$(PDF_FILE): $(TEX_FILE)
	luatex-pdf "$<"

# ステップ5: チャプター抽出
$(YOUTUBE_CHAPTERS) $(MV_CHAPTERS): $(TEX_FILE)
	tex2chapters "$<"

chapters: $(YOUTUBE_CHAPTERS)

clean:
	rm -f $(VIDEO_FILE) $(YT_SRT) $(WP_SRT) $(TEX_FILE) $(PDF_FILE) \
	      $(YOUTUBE_CHAPTERS) $(MV_CHAPTERS)

.PHONY: help
help:
	@echo "Rehearsal Report Generation Workflow"
	@echo ""
	@echo "Usage:"
	@echo "  make URL=\"https://youtu.be/VIDEO_ID\""
	@echo ""
	@echo "Targets:"
	@echo "  all       - Complete workflow (will fail at Claude step)"
	@echo "  download  - Download video and YouTube subtitles"
	@echo "  chapters  - Extract chapters from existing .tex file"
	@echo "  clean     - Remove all generated files"
```

### 利点
- ✅ **依存関係の明確化**: ファイル間の依存関係が視覚的に明確
- ✅ **部分実行**: 途中からの再実行が容易（`make chapters`など）
- ✅ **冪等性**: 既存ファイルがあればスキップ（時間節約）
- ✅ **標準ツール**: Makeは広く普及、学習コストが低い
- ✅ **並列実行**: `-j`オプションで並列処理可能（ただし今回は直列）

### 欠点
- ❌ **Claude統合不可**: AI分析ステップが自動化できない
- ❌ **動的ファイル名**: ytdl-claudeの出力ファイル名が実行前に不明
- ❌ **エラーハンドリング**: 複雑なエラー処理が困難
- ❌ **長時間処理**: Whisperの完了待ちが不自然（busy wait）
- ❌ **リモート実行**: whisper-remote, luatex-pdfのリモート処理が可視化されない

### 評価
**適合度: ⭐⭐☆☆☆ (2/5)**

Makefileは「ビルドツール」として設計されており、ファイル依存関係の管理には優れているが、以下の理由で本ワークフローには不適合：
1. Claude AIの介入が必須（完全自動化不可）
2. 長時間リモート処理（Whisper: 30分〜2時間）の管理が不得意
3. 動的に決まるファイル名への対応が複雑

---

## アプローチ2: Zshスクリプト

### 実装例

```bash
#!/usr/bin/env zsh
# rehearsal-workflow.zsh - リハーサル記録作成ワークフロー
# Usage: rehearsal-workflow.zsh <YouTube_URL>

set -euo pipefail

# ==============================================================================
# 設定
# ==============================================================================
readonly YOUTUBE_URL="$1"
readonly WORK_DIR="$(pwd)"
readonly LOG_FILE="${WORK_DIR}/workflow_$(date +%Y%m%d_%H%M%S).log"

# 色付きログ出力
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

log_info() {
    echo "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# ==============================================================================
# 引数チェック
# ==============================================================================
if [[ -z "${YOUTUBE_URL:-}" ]]; then
    echo "Usage: $0 <YouTube_URL>" >&2
    exit 1
fi

# ==============================================================================
# ステップ1: YouTube動画ダウンロード
# ==============================================================================
log_info "Step 1/5: Downloading YouTube video and subtitles..."

if ! ytdl-claude "$YOUTUBE_URL" -d 2>&1 | tee -a "$LOG_FILE"; then
    log_error "YouTube download failed"
    exit 1
fi

# ダウンロードされたファイルを検出
VIDEO_FILE=$(ls -t *.mp4 | head -1)
BASENAME="${VIDEO_FILE:r}"
YT_SRT="${BASENAME}_yt.srt"

if [[ ! -f "$VIDEO_FILE" ]] || [[ ! -f "$YT_SRT" ]]; then
    log_error "Expected files not found: $VIDEO_FILE, $YT_SRT"
    exit 1
fi

log_info "Downloaded: $VIDEO_FILE, $YT_SRT"

# ==============================================================================
# ステップ2: Whisper高精度文字起こし
# ==============================================================================
log_info "Step 2/5: Starting Whisper transcription (this may take 30min-2hours)..."

WP_SRT="${BASENAME}_wp.srt"

if [[ -f "$WP_SRT" ]]; then
    log_warn "Whisper output already exists: $WP_SRT (skipping)"
else
    if ! whisper-remote --demucs "$VIDEO_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log_error "Whisper transcription failed"
        exit 1
    fi

    # Whisper完了待ち（polling）
    log_info "Waiting for Whisper to complete..."
    local attempt=0
    local max_attempts=720  # 2時間（10秒間隔）

    while [[ ! -f "$WP_SRT" ]] && [[ $attempt -lt $max_attempts ]]; do
        sleep 10
        ((attempt++))

        if (( attempt % 30 == 0 )); then
            log_info "Still waiting... (${attempt}0 seconds elapsed)"
        fi
    done

    if [[ ! -f "$WP_SRT" ]]; then
        log_error "Whisper output not found after timeout"
        exit 1
    fi
fi

log_info "Whisper transcription completed: $WP_SRT"

# ==============================================================================
# ステップ3: Claude AI分析 → LaTeX生成（手動介入）
# ==============================================================================
log_warn "Step 3/5: Claude AI analysis required (manual step)"
log_warn ""
log_warn "Please perform the following:"
log_warn "  1. Run: claude code"
log_warn "  2. Provide this prompt:"
log_warn "     '${YT_SRT}と${WP_SRT}を統合分析し、リハーサル記録を詳細にLuaTeX形式で作成してください。'"
log_warn "  3. Save the output as: ${BASENAME}_リハーサル記録.tex"
log_warn ""
log_warn "Press Enter after completing the Claude AI step..."
read

TEX_FILE="${BASENAME}_リハーサル記録.tex"

if [[ ! -f "$TEX_FILE" ]]; then
    log_error "LaTeX file not found: $TEX_FILE"
    log_error "Please create it using Claude AI and try again"
    exit 1
fi

# ==============================================================================
# ステップ4: LuaLaTeX PDF生成
# ==============================================================================
log_info "Step 4/5: Compiling LaTeX to PDF..."

if ! luatex-pdf "$TEX_FILE" 2>&1 | tee -a "$LOG_FILE"; then
    log_error "LaTeX compilation failed"
    exit 1
fi

PDF_FILE="${TEX_FILE:r}.pdf"
log_info "PDF generated: $PDF_FILE"

# ==============================================================================
# ステップ5: チャプターリスト抽出
# ==============================================================================
log_info "Step 5/5: Extracting chapters..."

if ! tex2chapters "$TEX_FILE" 2>&1 | tee -a "$LOG_FILE"; then
    log_error "Chapter extraction failed"
    exit 1
fi

YOUTUBE_CHAPTERS="${TEX_FILE:r}_youtube.txt"
MV_CHAPTERS="${TEX_FILE:r}_movieviewer.txt"

# ==============================================================================
# 完了レポート
# ==============================================================================
log_info "========================================="
log_info "Workflow completed successfully!"
log_info "========================================="
log_info ""
log_info "Generated files:"
log_info "  - Video:            $VIDEO_FILE"
log_info "  - YouTube SRT:      $YT_SRT"
log_info "  - Whisper SRT:      $WP_SRT"
log_info "  - LaTeX:            $TEX_FILE"
log_info "  - PDF:              $PDF_FILE"
log_info "  - YouTube chapters: $YOUTUBE_CHAPTERS"
log_info "  - MV chapters:      $MV_CHAPTERS"
log_info ""
log_info "Log file: $LOG_FILE"
```

### 利点
- ✅ **柔軟性**: 条件分岐、ループ、エラーハンドリングが自由
- ✅ **可読性**: 処理フローが上から下へ直感的
- ✅ **エラー処理**: `set -euo pipefail`で堅牢性向上
- ✅ **ログ記録**: 全プロセスをログファイルに保存
- ✅ **進捗表示**: 色付きメッセージでユーザー体験向上
- ✅ **環境統合**: zsh固有機能（`${VAR:r}`など）を活用
- ✅ **手動介入対応**: Claude AIステップで明示的に待機

### 欠点
- ❌ **並列実行困難**: 複数URLの同時処理が煩雑
- ❌ **依存関係**: ファイル存在チェックを手動実装
- ❌ **保守性**: 複雑になるとデバッグが困難
- ❌ **再利用性**: スクリプト全体が1つの塊（モジュール化困難）

### 評価
**適合度: ⭐⭐⭐⭐☆ (4/5)**

Zshスクリプトは本ワークフローに最も適している：
1. ✅ 手動介入（Claude AI）を明示的に組み込める
2. ✅ 長時間処理（Whisper）のポーリングが実装可能
3. ✅ エラー処理とログ記録が充実
4. ✅ zsh環境に最適化（既存の`tex2chapters`などと統合）

減点理由：複数動画の並列処理やモジュール化には向かない

---

## アプローチ3: Claude Code カスタムスラッシュコマンド

### 実装例

`.claude/commands/rehearsal.md`:

```markdown
# /rehearsal - リハーサル記録作成ワークフロー

ユーザーが提供するYouTube URLから、以下のワークフローを実行してください：

## ワークフロー

1. **YouTube動画ダウンロード**
   - コマンド: `ytdl-claude "<URL>" -d`
   - 出力ファイルを確認し、`BASENAME`を特定

2. **Whisper文字起こし起動**
   - コマンド: `whisper-remote --demucs <VIDEO_FILE>`
   - ユーザーに「Whisperが完了したら`<BASENAME>_wp.srt`の存在を確認してください」と伝える

3. **SRTファイル統合分析**
   - `<BASENAME>_yt.srt`と`<BASENAME>_wp.srt`を読み込む
   - 以下の要件でLaTeXレポートを生成：
     - ドキュメントクラス: `ltjsarticle`, 2段組, A4
     - フォント: Libertinus（欧文）、原ノ味（日本語）
     - セクション構造: リハーサル概要、時系列展開、ホルン指示まとめ、音楽用語集
     - すべてのセクションにタイムスタンプ `[HH:MM:SS.mmm]` を付与
   - 保存先: `<BASENAME>_リハーサル記録.tex`

4. **PDF生成**
   - コマンド: `luatex-pdf <TEX_FILE>`

5. **チャプターリスト生成**
   - コマンド: `tex2chapters <TEX_FILE>`

6. **完了レポート**
   - 生成されたすべてのファイルをリストアップ
   - YouTubeチャプターの使い方を説明

## 引数

- `url`: YouTube動画のURL（必須）

## 使用例

```
/rehearsal url="https://youtu.be/VIDEO_ID"
```

## エラーハンドリング

- 各ステップでエラーが発生した場合、詳細なエラーメッセージを表示
- Whisperの完了を待つ際は、10分ごとに進捗確認を促す
```

### 利点
- ✅ **Claude AI統合**: AI分析が完全に自動化
- ✅ **対話的**: エラー時にユーザーと対話しながら修正可能
- ✅ **コンテキスト保持**: Claude Codeのセッション内で全情報を保持
- ✅ **柔軟な分析**: 動画内容に応じて適応的にレポート生成
- ✅ **自然言語**: プロンプト調整が容易（コード不要）
- ✅ **学習曲線**: 使用者はマークダウンのみ理解すればよい

### 欠点
- ❌ **実行環境依存**: Claude Codeが必須
- ❌ **トークン制限**: 長時間セッションでコンテキストが溢れる可能性
- ❌ **非決定的**: AI判断により結果が変動
- ❌ **デバッグ困難**: スラッシュコマンドのトラブルシューティングが不明瞭
- ❌ **バッチ処理**: 複数URLの処理が非効率

### 評価
**適合度: ⭐⭐⭐⭐⭐ (5/5)**

Claude Codeカスタムコマンドは、本ワークフローの**最適解**：
1. ✅ **最大の障壁を解決**: Claude AIによるSRT分析→LaTeX生成を完全自動化
2. ✅ **人間の介入を最小化**: Whisper完了確認のみ
3. ✅ **適応的処理**: 動画内容（曲目、時間、字幕品質）に応じて最適なレポート生成
4. ✅ **保守性**: `.md`ファイルで管理、プロンプト改善が容易
5. ✅ **エラー回復**: Claude Codeが自動的にリトライ・代替手段を提案

---

## アプローチ4: Task Runner (npm scripts / just)

### 実装例（just）

`justfile`:

```just
# justfile - Rehearsal workflow task runner

set shell := ["zsh", "-cu"]

# 変数
video_file := ""
basename := ""

# デフォルトタスク
default:
    @just --list

# YouTube動画ダウンロード
download URL:
    #!/usr/bin/env zsh
    echo "Downloading from {{URL}}..."
    ytdl-claude "{{URL}}" -d
    echo "Download complete!"

# Whisper文字起こし
whisper VIDEO:
    #!/usr/bin/env zsh
    echo "Starting Whisper transcription for {{VIDEO}}..."
    whisper-remote --demucs "{{VIDEO}}"
    echo "Whisper job submitted. Check for {{VIDEO:r}}_wp.srt"

# Claude分析（プレースホルダー）
analyze YT_SRT WP_SRT:
    @echo "ERROR: Manual Claude AI analysis required"
    @echo "Please analyze {{YT_SRT}} and {{WP_SRT}}"
    @exit 1

# PDF生成
compile TEX:
    #!/usr/bin/env zsh
    echo "Compiling {{TEX}} to PDF..."
    luatex-pdf "{{TEX}}"

# チャプター抽出
chapters TEX:
    #!/usr/bin/env zsh
    echo "Extracting chapters from {{TEX}}..."
    tex2chapters "{{TEX}}"

# 完全ワークフロー（download→whisper）
workflow URL:
    @just download {{URL}}
    @just whisper $(ls -t *.mp4 | head -1)
    @echo "Next: Wait for Whisper, then run Claude analysis"

# クリーンアップ
clean PATTERN:
    rm -f {{PATTERN}}*
```

使用例:
```bash
just workflow "https://youtu.be/VIDEO_ID"
just compile "リハーサル記録.tex"
just chapters "リハーサル記録.tex"
```

### 利点
- ✅ **シンプルな構文**: Makefileより読みやすい
- ✅ **タスク単位**: 小さな処理を組み合わせやすい
- ✅ **引数渡し**: パラメータ化されたタスク
- ✅ **クロスプラットフォーム**: `just`はRust製で移植性高い

### 欠点
- ❌ **追加ツール必要**: `just`のインストールが必要
- ❌ **依存関係管理**: Makefileより弱い
- ❌ **Claude統合不可**: AI分析が自動化できない
- ❌ **学習コスト**: 新しいツールの習得が必要

### 評価
**適合度: ⭐⭐⭐☆☆ (3/5)**

Task runnerは中間的なアプローチで、Makefileより使いやすいがClaude統合がないため本質的な制約は同じ。

---

## アプローチ5: Python + Luigi/Airflow（ワークフローエンジン）

### 実装例（概念）

```python
# rehearsal_pipeline.py
import luigi
import subprocess
from pathlib import Path

class DownloadVideo(luigi.Task):
    url = luigi.Parameter()

    def output(self):
        # 動的に決まるファイル名を予測（困難）
        return luigi.LocalTarget("video.mp4")

    def run(self):
        subprocess.run(["ytdl-claude", self.url, "-d"], check=True)

class WhisperTranscribe(luigi.Task):
    url = luigi.Parameter()

    def requires(self):
        return DownloadVideo(url=self.url)

    def output(self):
        return luigi.LocalTarget("video_wp.srt")

    def run(self):
        video = self.input().path
        subprocess.run(["whisper-remote", "--demucs", video], check=True)
        # Whisper完了待ち...（polling実装）

class GenerateLaTeX(luigi.Task):
    url = luigi.Parameter()

    def requires(self):
        return WhisperTranscribe(url=self.url)

    def output(self):
        return luigi.LocalTarget("rehearsal_report.tex")

    def run(self):
        # Claude AI呼び出し（困難）
        raise NotImplementedError("Claude AI integration required")

# ... 以下同様
```

### 利点
- ✅ **エンタープライズ級**: 大規模ワークフローに対応
- ✅ **可視化**: DAGベースのワークフロー可視化
- ✅ **並列処理**: 複数タスクの並列実行
- ✅ **リトライ機能**: 自動リトライ・エラー通知

### 欠点
- ❌ **過剰設計**: 本ワークフローには大げさ
- ❌ **学習コスト**: Luigi/Airflowの習得が必要
- ❌ **セットアップ**: 複雑な環境構築
- ❌ **Claude統合困難**: AI分析ステップの統合が不自然
- ❌ **オーバーヘッド**: 小規模タスクには重すぎる

### 評価
**適合度: ⭐☆☆☆☆ (1/5)**

エンタープライズワークフローエンジンは、本プロジェクトの規模には不適合。複数動画を毎日処理するなら検討余地あり。

---

## 総合比較表

| 項目 | Makefile | Zshスクリプト | Claude Code | Task Runner | Workflow Engine |
|------|----------|--------------|-------------|-------------|-----------------|
| **Claude統合** | ❌ 不可 | ❌ 手動 | ✅ 完全自動 | ❌ 不可 | ❌ 困難 |
| **依存関係管理** | ✅ 優秀 | ⚠️ 手動 | ✅ 自動 | ⚠️ 手動 | ✅ 優秀 |
| **エラー処理** | ❌ 弱い | ✅ 柔軟 | ✅ 自動 | ⚠️ 普通 | ✅ 優秀 |
| **長時間処理** | ❌ 不得意 | ✅ 対応可 | ✅ 対応可 | ⚠️ 普通 | ✅ 優秀 |
| **並列実行** | ✅ 対応 | ❌ 困難 | ❌ 非効率 | ⚠️ 可能 | ✅ 優秀 |
| **学習コスト** | ⚠️ 低〜中 | ✅ 低 | ✅ 低 | ⚠️ 中 | ❌ 高 |
| **保守性** | ⚠️ 普通 | ⚠️ 普通 | ✅ 優秀 | ✅ 良好 | ⚠️ 複雑 |
| **セットアップ** | ✅ 不要 | ✅ 不要 | ✅ 既存 | ❌ 必要 | ❌ 複雑 |
| **適応性** | ❌ 低 | ⚠️ 中 | ✅ 高 | ⚠️ 中 | ✅ 高 |
| **適合度** | ⭐⭐☆☆☆ | ⭐⭐⭐⭐☆ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐☆☆ | ⭐☆☆☆☆ |

---

## 評価基準

### 1. Claude AI統合（最重要）
- **重み: 40%**
- 理由: SRT分析→LaTeX生成は最も時間がかかり、AI判断が必須

### 2. 保守性・拡張性
- **重み: 20%**
- 理由: 今後も複数のリハーサルで使用予定

### 3. エラー処理・ロバスト性
- **重み: 15%**
- 理由: リモート処理（Whisper, luatex-pdf）が失敗する可能性

### 4. 学習コスト
- **重み: 15%**
- 理由: ユーザー（ホルン奏者）が技術者とは限らない

### 5. 実行効率
- **重み: 10%**
- 理由: 動画処理は時間がかかるが、並列化の必要性は低い

---

## 推奨アプローチ

### 🏆 第1位: Claude Code カスタムスラッシュコマンド + Zshヘルパー関数（ハイブリッド）

#### 構成

1. **`.claude/commands/rehearsal.md`** - Claude Codeスラッシュコマンド
   - ワークフロー全体のオーケストレーション
   - SRT分析 → LaTeX生成（AI処理）

2. **`~/.config/zsh/functions/rehearsal-download`** - zsh関数
   - YouTube動画ダウンロード + Whisper起動
   - 完了確認

3. **`~/.config/zsh/functions/rehearsal-finalize`** - zsh関数
   - PDF生成 + チャプター抽出
   - 成果物レポート

#### ワークフロー

```bash
# ステップ1: ダウンロード + Whisper起動（zsh関数）
$ rehearsal-download "https://youtu.be/VIDEO_ID"
# → video.mp4, video_yt.srt をダウンロード
# → whisper-remote を起動
# → "Whisperが完了したら /rehearsal を実行してください" と表示

# ステップ2: Claude AI分析 + LaTeX生成（Claudeコマンド）
$ claude code
> /rehearsal

# ステップ3: PDF生成 + チャプター抽出（zsh関数）
$ rehearsal-finalize "リハーサル記録.tex"
# → PDF生成
# → チャプター抽出
# → 成果物レポート表示
```

#### 理由

1. **最適な責任分離**:
   - 機械的処理（ダウンロード、コンパイル、抽出）→ zsh
   - AI判断処理（分析、レポート生成）→ Claude Code

2. **各ツールの強みを活用**:
   - zshは高速・軽量なファイル操作に最適
   - Claude Codeは複雑な分析・文書生成に最適

3. **ユーザー体験**:
   - 3つの明確なステップ（download → analyze → finalize）
   - 各ステップで進捗確認可能
   - エラー時の介入ポイントが明確

4. **保守性**:
   - zsh関数: シンプルなファイル操作のみ
   - Claude Code: プロンプト調整が容易（`.md`ファイル編集）

#### 実装コスト
- **低**: 既存の`tex2chapters`と同様のzsh関数を2つ追加
- **低**: `.claude/commands/rehearsal.md`を作成

---

### 🥈 第2位: Zshスクリプト単体（Claude手動介入）

#### 構成
- `~/bin/rehearsal-workflow.zsh` - 上述の完全版zshスクリプト

#### 使用方法
```bash
$ rehearsal-workflow.zsh "https://youtu.be/VIDEO_ID"
# ダウンロード → Whisper → 【Claude手動介入】→ PDF → チャプター
```

#### 理由
- シンプルで理解しやすい
- 1つのファイルで完結
- Claude Code不要（汎用性）

#### 欠点
- Claude分析が手動（最大のボトルネック）

---

### 🥉 第3位: Makefileベース（教育目的）

#### 理由
- 依存関係の学習に有用
- 他プロジェクトへの応用

#### 欠点
- 実用性は低い（Claude統合不可）

---

## 実装推奨: ハイブリッドアプローチ

### ファイル構成

```
~/.config/zsh/functions/
├── tex2chapters              # 既存
├── rehearsal-download        # 新規
└── rehearsal-finalize        # 新規

~/.claude/commands/
└── rehearsal.md              # 新規

~/bin/
└── (不要)
```

### 次のステップ

1. `rehearsal-download` zsh関数を作成
2. `rehearsal-finalize` zsh関数を作成
3. `.claude/commands/rehearsal.md` を作成
4. `~/.config/zsh/functions/README.md` を更新
5. 実際のYouTube URLでテスト実行

---

## 結論

**本プロジェクトのベストプラクティスは「Claude Code カスタムスラッシュコマンド + Zshヘルパー関数のハイブリッド構成」である。**

### 理由まとめ

1. **Claude AI統合が最大の価値**:
   - 2つのSRTファイルを分析し、音楽的に意味のあるレポートを生成するのはAIの独壇場
   - 指揮者の指示を適切にカテゴライズし、ホルン向け指示を抽出するには文脈理解が必須

2. **段階的実行が実用的**:
   - Whisperは30分〜2時間かかる → 完全自動化より段階実行が現実的
   - 各ステップで成果物を確認できることが重要

3. **保守性と拡張性**:
   - プロンプト改善が容易（`.md`ファイル編集）
   - 新しい曲目や形式への対応が柔軟

4. **学習コストが最小**:
   - ユーザーは既存のClaude Code環境を活用
   - zsh関数は既存の`tex2chapters`と同じパターン

5. **既存環境との親和性**:
   - `tex2chapters`, `ytdl-claude`, `whisper-remote`, `luatex-pdf`をそのまま活用
   - 新しいツールのインストール不要

この設計により、**「1つのYouTube URLから3コマンドで完全なリハーサル記録を生成」**という理想的なワークフローが実現される。
