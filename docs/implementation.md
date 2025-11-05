# リハーサル記録作成ワークフロー実装完了

**作成日**: 2025-11-05
**実装内容**: YouTubeリンク → PDF + チャプターリスト の自動化ワークフロー

---

## 実装サマリー

ハイブリッドアプローチ（**Claude Code カスタムスラッシュコマンド + Zshヘルパー関数**）により、1つのYouTube URLから**3ステップ**で完全なリハーサル記録を生成できるワークフローを実装しました。

### 実装ファイル

1. **`~/.config/zsh/functions/rehearsal-download`** (176行)
   - YouTube動画ダウンロード + Whisper文字起こし起動

2. **`~/.config/zsh/functions/rehearsal-finalize`** (183行)
   - PDF生成 + チャプターリスト抽出

3. **`~/.claude/commands/rehearsal.md`** (321行)
   - Claude AI分析 + LaTeX生成スラッシュコマンド

4. **`~/.config/zsh/functions/README.md`** (更新)
   - ワークフロー全体のドキュメント

---

## 使用方法

### 完全ワークフロー（3ステップ）

```bash
# ステップ1: ダウンロード + Whisper起動
$ rehearsal-download "https://youtu.be/VIDEO_ID"
# → 動画.mp4, 動画_yt.srt をダウンロード
# → whisper-remote を起動
# → "Whisperが完了したら /rehearsal を実行してください" と表示

# ステップ2: AI分析 + LaTeX生成（Whisper完了後）
$ claude code
> /rehearsal
# → 前提条件を質問（ファイル名、団体名、指揮者、曲目、著者）
# → 両方のSRTファイルを統合分析
# → LuaTeX形式リハーサル記録を生成
# → ファイル保存

# ステップ3: PDF生成 + チャプター抽出
$ rehearsal-finalize "リハーサル記録.tex"
# → PDFコンパイル（luatex-pdf）
# → YouTubeチャプターリスト生成
# → Movie Viewerチャプターリスト生成
# → 成果物レポート表示
```

### 生成される成果物

各ステップで以下のファイルが生成されます：

**ステップ1後**:
- `YYYYMMDD_タイトル.mp4` - 動画ファイル
- `YYYYMMDD_タイトル_yt.srt` - YouTube自動生成字幕
- `YYYYMMDD_タイトル_wp.srt` - Whisper高精度字幕（30分〜2時間後）

**ステップ2後**:
- `YYYYMMDD_曲名_リハーサル記録.tex` - LuaTeX形式レポート

**ステップ3後**:
- `YYYYMMDD_曲名_リハーサル記録.pdf` - PDF形式レポート
- `YYYYMMDD_曲名_リハーサル記録_youtube.txt` - YouTubeチャプター
- `YYYYMMDD_曲名_リハーサル記録_movieviewer.txt` - Movie Viewerチャプター

---

## セットアップ方法

### 1. Zsh関数のロード

`~/.zshrc`に以下を追加（まだの場合）：

```bash
# カスタムzsh関数のロード
fpath=(~/.config/zsh/functions $fpath)
autoload -Uz tex2chapters rehearsal-download rehearsal-finalize
```

設定を反映：

```bash
source ~/.zshrc
```

### 2. Claude Codeスラッシュコマンドの確認

`~/.claude/commands/rehearsal.md` が存在することを確認：

```bash
ls -l ~/.claude/commands/rehearsal.md
```

Claude Code内で `/rehearsal` が利用可能になります。

### 3. 依存ツールの確認

以下のツールが利用可能であることを確認：

```bash
which ytdl-claude       # YouTube動画ダウンロード
which whisper-remote    # Whisper文字起こし
which luatex-pdf        # LuaLaTeXコンパイル
```

---

## 技術仕様

### ステップ1: `rehearsal-download`

#### 機能
- YouTube動画と字幕をダウンロード（`ytdl-claude -d`）
- 最新のmp4ファイルを自動検出
- Whisper高精度文字起こしを起動（`whisper-remote --demucs`）
- 次のステップの案内を表示

#### 特徴
- ✅ 色付きログ出力（INFO/WARN/ERROR/STEP）
- ✅ ファイルサイズ・行数の表示
- ✅ エラーハンドリング（URL検証、ファイル存在確認）
- ✅ 既存Whisper字幕のスキップ

#### 処理時間
- ダウンロード: 1〜5分（動画サイズによる）
- Whisper: 30分〜2時間（動画長、リモートサーバー負荷による）

---

### ステップ2: `/rehearsal` (Claude Code)

#### 機能
- 前提条件の質問（ファイル名、団体情報、著者）
- YouTube字幕（`*_yt.srt`）とWhisper字幕（`*_wp.srt`）の統合分析
- 指揮者の指示を文脈に沿って校正・補足
- タイムスタンプ付きLuaTeX形式レポート生成

#### 分析方針

**YouTube字幕の役割**:
- 時系列構造の把握（動画全体をカバー）
- 演奏セクションの特定
- リハーサルの流れの理解

**Whisper字幕の役割**:
- 指揮者の指示の高精度記録
- 技術的アドバイスの正確な抽出
- 音楽用語の正確な認識

**統合分析**:
- 両方の長所を活かし最も正確な記録を生成
- 誤認識を文脈から修正（例：「ホルモン」→「ホルン」）
- 指示の対象パート、楽譜上の位置を明記

#### 出力構造

1. **リハーサル概要** - 基本情報、時系列、データソース
2. **時系列展開** - 曲ごと・楽章ごとのセクション
3. **パート別指示まとめ** - 著者のパート向け指示抽出
4. **音楽用語集** - イタリア語音楽用語の説明
5. **擬音語パターン** - 指揮者の口唱記録
6. **リハーサルの特徴** - 指揮者の教育スタイル
7. **重要な瞬間** - キーシーンの記録
8. **Summary** - 総括、謝辞

#### タイムスタンプ形式

すべてのセクション・サブセクションに `[HH:MM:SS.mmm]` を付与：

```latex
\section{リハーサル概要 [00:00:06]}
\subsection{冒頭部分の練習 [00:11:35.959]}
\subsubsection{ホルン3番・4番への音色指導 [00:13:12.880]}
```

これにより、後のステップでYouTube/Movie Viewerチャプターを自動抽出可能。

#### LuaTeX仕様

- **ドキュメントクラス**: `\documentclass[a4paper,10pt,twocolumn]{ltjsarticle}`
- **欧文フォント**: Libertinus Serif/Sans/Mono
- **日本語フォント**: 原ノ味明朝/ゴシック（HaranoAji）
- **数式フォント**: Libertinus Math
- **ヘッダー**: 生成日時（JST）+ ページ番号
- **ハイパーリンク**: 青色
- **余白**: 20mm

---

### ステップ3: `rehearsal-finalize`

#### 機能
- LuaLaTeX PDFコンパイル（`luatex-pdf`、リモートサーバー経由）
- チャプターリスト抽出（`tex2chapters`関数呼び出し）
- 成果物レポートの表示
- 次のアクションの提案

#### 特徴
- ✅ PDF情報の詳細表示（ページ数、ファイルサイズ）
- ✅ チャプター数の集計
- ✅ 最初の3チャプターのプレビュー
- ✅ 次のアクションの提案（PDFを開く、クリップボードコピーなど）

#### 処理時間
- PDFコンパイル: 1〜3分（リモートサーバー処理）
- チャプター抽出: 数秒

#### 生成されるチャプター形式

**YouTube形式** (`*_youtube.txt`):
```
00:00:06 リハーサル概要
00:11:35 冒頭部分の練習
00:13:12 ホルン3番・4番への音色指導
```
- **用途**: YouTube動画説明欄にコピー＆ペースト
- **形式**: `HH:MM:SS タイトル`（ミリ秒なし）

**Movie Viewer形式** (`*_movieviewer.txt`):
```
0:00:06.000 リハーサル概要
0:11:35.959 冒頭部分の練習
0:13:12.880 ホルン3番・4番への音色指導
```
- **用途**: Movie Viewer (https://github.com/mashi727/movie-viewer) での精密編集
- **形式**: `H:MM:SS.mmm タイトル`（ミリ秒3桁、時間の先頭0除去）

---

## ベストプラクティス選定理由

### なぜこのハイブリッドアプローチが最適か

#### 1. Claude AI統合が最大の価値（評価ウェイト: 40%）

**課題**: 2つのSRTファイル（YouTube + Whisper）を分析し、音楽的に意味のあるレポートを生成するのは、AIの独壇場。

**解決**: Claude Code `/rehearsal` スラッシュコマンドにより、以下が自動化：
- 両SRTファイルの統合分析
- 指揮者の指示の文脈理解と校正
- 音楽用語の正確な認識
- パート別指示の抽出
- タイムスタンプ付きセクション構成

**代替手段との比較**:
- ❌ **Makefile**: AI統合不可（最大のボトルネック）
- ❌ **Zshスクリプト単体**: 手動介入が必要
- ⚠️ **Task Runner**: AI統合困難
- ❌ **Workflow Engine**: AI統合が不自然

#### 2. 最適な責任分離

**機械的処理** → **Zsh関数**:
- ファイルダウンロード（`ytdl-claude`）
- Whisper起動（`whisper-remote`）
- PDFコンパイル（`luatex-pdf`）
- チャプター抽出（パターンマッチング）

**AI判断処理** → **Claude Code**:
- SRT分析（6000行以上の字幕）
- 文脈理解（音楽的意味）
- 誤認識修正（「ホルモン」→「ホルン」）
- レポート構成（セクション分け）

#### 3. ユーザー体験の最適化

**3つの明確なステップ**:
1. `rehearsal-download` - 機械的処理（待ち時間あり）
2. `/rehearsal` - AI処理（対話的）
3. `rehearsal-finalize` - 機械的処理（最終成果物）

**各ステップで進捗確認可能**:
- Whisperの完了待ち（`*_wp.srt`ファイル確認）
- LaTeXファイルの確認（内容レビュー可能）
- 最終成果物の確認（PDF、チャプター）

**エラー時の介入ポイントが明確**:
- ステップ1: ダウンロード失敗 → URL確認
- ステップ2: SRT分析失敗 → ファイル確認、情報再入力
- ステップ3: PDFコンパイル失敗 → TeXファイル修正

#### 4. 保守性・拡張性（評価ウェイト: 20%）

**Zsh関数**:
- シンプルなファイル操作のみ
- 既存の`tex2chapters`と同じパターン
- 変更が容易（シェルスクリプト）

**Claude Code**:
- プロンプト調整が容易（`.md`ファイル編集）
- 新しい曲目や形式への対応が柔軟
- 音楽用語集の拡充が簡単

#### 5. 学習コスト最小（評価ウェイト: 15%）

**ユーザー（ホルン奏者）視点**:
- 新しいツールのインストール不要
- 既存のClaude Code環境を活用
- 3つのコマンドを覚えるだけ

**開発者視点**:
- zsh関数は既存パターンを踏襲
- Claude Codeはマークダウン編集のみ
- 段階的なデバッグが可能

---

## 他のアプローチとの詳細比較

### 比較表

| 評価項目 | Makefile | Zshスクリプト | Claude Code<br>ハイブリッド | Task Runner | Workflow<br>Engine |
|---------|----------|-------------|---------------------------|-------------|-------------------|
| **Claude統合** | ❌ 不可 | ❌ 手動 | ✅ 完全自動 | ❌ 不可 | ❌ 困難 |
| **依存関係管理** | ✅ 優秀 | ⚠️ 手動 | ✅ 自動 | ⚠️ 手動 | ✅ 優秀 |
| **エラー処理** | ❌ 弱い | ✅ 柔軟 | ✅ 自動 | ⚠️ 普通 | ✅ 優秀 |
| **長時間処理** | ❌ 不得意 | ✅ 対応可 | ✅ 対応可 | ⚠️ 普通 | ✅ 優秀 |
| **並列実行** | ✅ 対応 | ❌ 困難 | ❌ 非効率 | ⚠️ 可能 | ✅ 優秀 |
| **学習コスト** | ⚠️ 低〜中 | ✅ 低 | ✅ 低 | ⚠️ 中 | ❌ 高 |
| **保守性** | ⚠️ 普通 | ⚠️ 普通 | ✅ 優秀 | ✅ 良好 | ⚠️ 複雑 |
| **セットアップ** | ✅ 不要 | ✅ 不要 | ✅ 既存 | ❌ 必要 | ❌ 複雑 |
| **適応性** | ❌ 低 | ⚠️ 中 | ✅ 高 | ⚠️ 中 | ✅ 高 |
| **総合評価** | ⭐⭐☆☆☆ | ⭐⭐⭐⭐☆ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐☆☆ | ⭐☆☆☆☆ |

### 評価基準（重み付け）

1. **Claude AI統合** (40%) - SRT分析→LaTeX生成の自動化
2. **保守性・拡張性** (20%) - 今後の複数リハーサルでの使用
3. **エラー処理・ロバスト性** (15%) - リモート処理の失敗対応
4. **学習コスト** (15%) - ユーザー（ホルン奏者）の習得容易性
5. **実行効率** (10%) - 並列化の必要性は低い

---

## 実装の技術的詳細

### `rehearsal-download` のポイント

```bash
# ダウンロード前後のmp4ファイル数を比較して新規ファイルを検出
local before_count=$(ls -1 *.mp4 2>/dev/null | wc -l | tr -d ' ')
ytdl-claude "$youtube_url" -d
local after_count=$(ls -1 *.mp4 2>/dev/null | wc -l | tr -d ' ')

# 最新のmp4ファイルを取得（タイムスタンプ順）
local video_file=$(ls -t *.mp4 2>/dev/null | head -1)

# ベースネーム取得（zsh固有の構文）
local basename="${video_file:r}"
```

### `rehearsal-finalize` のポイント

```bash
# PDF情報の取得（pdfinfo使用）
local pdf_size=$(du -h "$pdf_file" | cut -f1)
local pdf_pages=$(pdfinfo "$pdf_file" 2>/dev/null | grep "Pages:" | awk '{print $2}')

# tex2chapters関数の存在確認
if ! type tex2chapters &>/dev/null; then
    log_error "tex2chapters function not found"
    return 1
fi

# クリップボードへのコピー提案
echo "cat \"${youtube_chapters}\" | pbcopy"
```

### `/rehearsal` のポイント

- **前提条件の質問**: `AskUserQuestion`ツールを使用（想定）
- **大規模SRT読み込み**: `Read`ツールで`offset`/`limit`活用
- **統合分析**: Task toolで両SRTを完全分析（前回の実績）
- **LaTeX生成**: `Write`ツールで直接保存
- **コンパイル**: 必要に応じて`luatex-pdf`呼び出し

---

## トラブルシューティング

### 関数が見つからない

```bash
# fpath の確認
echo $fpath | grep ".config/zsh/functions"

# 関数の明示的な読み込み
autoload -Uz rehearsal-download rehearsal-finalize tex2chapters
```

### Whisperが完了しない

```bash
# Whisper字幕ファイルの確認
ls -lh *_wp.srt

# リモートサーバーの状態確認（whisper-remoteのログ確認）
# （whisper-remote固有の方法による）
```

### PDFコンパイルエラー

```bash
# LaTeXファイルの構文確認
# （手動でTeXファイルを確認）

# フォントの確認
fc-list | grep -i libertinus
fc-list | grep -i harano

# リモートサーバーの状態確認
# （luatex-pdf固有の方法による）
```

### チャプター抽出エラー

```bash
# TeXファイル内のタイムスタンプ形式確認
grep -E '\\(section|subsection|subsubsection).*\[' リハーサル記録.tex

# 手動でtex2chapters実行
tex2chapters リハーサル記録.tex
```

---

## 今後の拡張案

### 短期的改善

1. **Whisper完了通知**
   - リモートサーバーからの完了通知機能
   - メール/Slack通知の統合

2. **バッチ処理**
   - 複数URLの一括ダウンロード
   - `list.txt`からの自動処理

3. **エラーリカバリー**
   - Whisper失敗時の自動リトライ
   - 部分的な字幕での処理継続

### 長期的拡張

1. **マルチカメラ対応**
   - 複数視点の動画を統合処理
   - カメラアングルごとの分析

2. **楽譜連携**
   - MusicXML/PDFとの対応付け
   - 小節番号の自動抽出

3. **アーカイブ管理**
   - 複数リハーサルの横断検索
   - 指揮者の指示パターン分析

4. **Web UI**
   - ブラウザベースのワークフロー管理
   - 進捗状況の可視化

---

## まとめ

### 実装成果

✅ **3ファイル、計680行のコード**を実装し、YouTubeリンクからPDF+チャプターリストまでの完全自動化ワークフローを構築しました。

✅ **ハイブリッドアプローチ**により、Claude AIの強み（分析・文書生成）とZshの強み（機械的処理）を最適に組み合わせました。

✅ **ユーザー体験**を重視し、3つの明確なステップ、色付きログ、次のアクション提案により、技術者でなくても使いやすい設計にしました。

### ワークフローの価値

このワークフローにより、**リハーサル動画の価値が飛躍的に向上**します：

1. **参加できなかったメンバー**が詳細な記録で完全にキャッチアップ
2. **指揮者の指示**が文脈と共に正確に記録され、復習が容易
3. **パート別指示**が明確に抽出され、個人練習に活用可能
4. **YouTubeチャプター**により動画の検索性が向上
5. **Movie Viewerチャプター**により精密な編集・レビューが可能

### 次のステップ

実装は完了しました。以下を実行してワークフローを開始できます：

```bash
# セットアップ（初回のみ）
source ~/.zshrc

# ワークフロー開始
rehearsal-download "https://youtu.be/YOUR_VIDEO_ID"
```

詳細は `~/.config/zsh/functions/README.md` を参照してください。
