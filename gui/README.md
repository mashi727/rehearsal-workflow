# Rehearsal Workflow GUI

**バージョン**: 1.0.0
**作成日**: 2025-11-06

リハーサル記録作成ワークフローのグラフィカルフロントエンド。YouTube動画URLから最終PDF・チャプター生成までの3ステップを可視化・実行します。

---

## 概要

このGUIは、`rehearsal-workflow`のコマンドラインツールをグラフィカルに操作するためのPySide6ベースのアプリケーションです。

### 主要機能

- **3ステップワークフローの可視化**
  - Step 1: YouTube動画ダウンロード + Whisper文字起こし
  - Step 2: Claude AI分析 + LaTeX生成
  - Step 3: PDF生成 + チャプター抽出

- **リアルタイムログ表示**
  - 各ステップの進行状況を色分けして表示
  - プロセス出力をリアルタイム監視

- **ファイル自動検出**
  - 生成されたファイル（動画、字幕、PDF、チャプター）を自動検出
  - ファイル存在状況を2秒ごとに更新

- **リハーサル情報入力**
  - 日付、団体名、指揮者、曲名、本番日程、著者
  - Whisper設定（Demucs音源分離オプション）

---

## スクリーンショット

```
┌─────────────────────────────────────────────────────────────────┐
│ Rehearsal Workflow GUI - リハーサル記録作成                      │
├─────────────────────┬───────────────────────────────────────────┤
│  📝 基本情報         │  実行ログ                                  │
│  🔄 ワークフロー      │  [INFO] Rehearsal Workflow GUI 起動       │
│  📁 生成ファイル      │  [STEP] Step 1から開始してください         │
│                     │  [INFO] カレントディレクトリ: ...          │
│ Step 1: YouTube動画  │  [SUCCESS] Step 1完了                     │
│ ダウンロード+Whisper │  [STEP] Step 2に進んでください             │
│ [📥 ダウンロード開始] │                                           │
│                     │                                           │
│ Step 2: AI分析      │                                           │
│ + LaTeX生成         │                                           │
│ [✅ ステップ2完了]   │                                           │
│                     │                                           │
│ Step 3: PDF生成     │                                           │
│ + チャプター抽出     │                                           │
│ [📄 PDF生成開始]    │                                           │
│                     │                                           │
│ [■■■■■■■■□□□] 66%│                                           │
└─────────────────────┴───────────────────────────────────────────┘
```

---

## インストール

### 前提条件

1. **rehearsal-workflow本体がインストール済み**
   ```bash
   cd rehearsal-workflow
   ./scripts/install.sh
   ```

2. **Python 3.8以上**
   ```bash
   python3 --version
   ```

### GUI依存パッケージのインストール

```bash
cd rehearsal-workflow/gui
pip3 install -r requirements.txt
```

インストールされるパッケージ:
- `PySide6` (Qt for Python 6.6.0以上)

---

## 使用方法

### 1. GUI起動

```bash
cd /path/to/work/directory  # 作業ディレクトリに移動
python3 ~/path/to/rehearsal-workflow/gui/rehearsal_gui.py
```

**重要**: GUIはカレントディレクトリで動作します。リハーサル動画を保存したいディレクトリで起動してください。

### 2. 基本情報タブで情報入力

「📝 基本情報」タブで以下を入力:

- **YouTube動画URL**（必須）: `https://youtu.be/VIDEO_ID`
- **リハーサル日付**: `2025-11-02`
- **団体名**: `創価大学 新世紀管弦楽団`
- **指揮者**: `阪本正彦先生`
- **曲名**: `ドヴォルザーク交響曲第8番`
- **本番日程**: `2025-12-14`
- **著者**: `ホルン奏者有志`
- **Whisper設定**: 音源分離（Demucs）を使用するか選択

### 3. ワークフロータブで実行

「🔄 ワークフロー」タブに切り替え:

#### Step 1: YouTube動画ダウンロード + Whisper起動

1. 「📥 ダウンロード開始」ボタンをクリック
2. `rehearsal-download` が実行される
3. 右側のログで進行状況を確認
4. 完了すると「Whisper処理中...」と表示される（30分〜2時間）

**出力**:
- `YYYYMMDD_タイトル.mp4` - 動画ファイル
- `YYYYMMDD_タイトル_yt.srt` - YouTube自動生成字幕
- `YYYYMMDD_タイトル_wp.srt` - Whisper高精度字幕（後に生成）

#### Step 2: Claude AI分析 + LaTeX生成

**重要**: このステップはClaude Codeで**手動実行**します。

1. Whisper処理が完了するまで待つ（`*_wp.srt`ファイルが生成されるまで）
2. ターミナルで以下を実行:
   ```bash
   claude code
   ```
3. Claude Code内で以下を入力:
   ```
   /rehearsal
   ```
4. Claude AIからの質問に回答:
   - YouTube字幕ファイル名: `YYYYMMDD_*_yt.srt`
   - Whisper字幕ファイル名: `YYYYMMDD_*_wp.srt`
   - リハーサル情報（基本情報タブで入力した内容を回答）
5. LaTeXファイルが生成される: `YYYYMMDD_曲名_リハーサル記録.tex`
6. GUIに戻り、「✅ ステップ2完了」ボタンをクリック
7. ファイル選択ダイアログで生成されたLaTeXファイルを選択

**出力**:
- `YYYYMMDD_曲名_リハーサル記録.tex` - LaTeX形式リハーサル記録

#### Step 3: PDF生成 + チャプター抽出

1. 「📄 PDF生成開始」ボタンをクリック
2. `rehearsal-finalize` が実行される
3. LuaLaTeX PDFコンパイル（リモートサーバー経由、1〜3分）
4. チャプターリスト生成
5. 完了ダイアログが表示される

**出力**:
- `YYYYMMDD_曲名_リハーサル記録.pdf` - PDF形式リハーサル記録
- `YYYYMMDD_曲名_リハーサル記録_youtube.txt` - YouTubeチャプターリスト（`HH:MM:SS`形式）
- `YYYYMMDD_曲名_リハーサル記録_movieviewer.txt` - Movie Viewerチャプターリスト（`H:MM:SS.mmm`形式）

### 4. 生成ファイルタブで確認

「📁 生成ファイル」タブで各ファイルの生成状況を確認できます。ファイルは2秒ごとに自動検出されます。

---

## GUI設計の特徴

### 元の`video_analysis_gui.py`からの改善点

1. **ワークフロー特化**: 汎用的な動画分析GUIから、リハーサル記録作成に特化
2. **3ステップの明確化**: ダウンロード → AI分析 → PDF生成の流れを可視化
3. **ファイル自動検出**: 手動でファイルパスを入力する必要がない
4. **リアルタイムログ**: プロセス出力をカラーコード付きで表示
5. **既存コマンドとの統合**: `rehearsal-download`, `/rehearsal`, `rehearsal-finalize`を直接呼び出し

### アーキテクチャ

```python
RehearsalWorkflowGUI (QMainWindow)
├── MetadataInputWidget (基本情報入力)
│   ├── YouTube URL
│   ├── リハーサル情報（日付、団体、指揮者、曲名...）
│   └── Whisper設定
├── WorkflowControlWidget (ワークフロー制御)
│   ├── Step 1ボタン + ステータス
│   ├── Step 2ボタン + ステータス
│   ├── Step 3ボタン + ステータス
│   └── プログレスバー
├── FileMonitorWidget (ファイル監視)
│   └── 生成ファイル一覧（2秒ごと更新）
└── LogViewer (リアルタイムログ)
    └── 色分けログ出力（INFO, WARN, ERROR, STEP, SUCCESS）
```

### データモデル

```python
@dataclass
class RehearsalMetadata:
    # 必須情報
    youtube_url: str
    rehearsal_date: str
    organization: str
    conductor: str
    piece_name: str
    concert_date: str
    author: str

    # ファイル情報（自動検出）
    video_file: str
    yt_srt_file: str
    wp_srt_file: str
    tex_file: str
    pdf_file: str
    youtube_chapters: str
    movieviewer_chapters: str

    # ワークフロー状態
    step: WorkflowStep
    step_message: str

    # Whisper設定
    use_demucs: bool
```

---

## 依存関係

### 必須

- **Python 3.8+**
- **PySide6** (Qt for Python)
- **rehearsal-workflow** 本体
  - `rehearsal-download` (Zsh関数)
  - `rehearsal-finalize` (Zsh関数)
  - `/rehearsal` (Claude Codeコマンド)

### システム依存

- **Zsh**: 関数実行のため
- **ytdl**: YouTube動画ダウンロード（ytdl-claude関数）
- **whisper-remote**: Whisper文字起こし（リモートGPU）
- **luatex-pdf**: LuaLaTeX PDFコンパイル（リモートDocker）
- **Claude Code**: AI分析エンジン

---

## トラブルシューティング

### 1. 「rehearsal-download: command not found」

**原因**: Zsh関数がロードされていない

**解決**:
```bash
# .zshrcに以下が記載されているか確認
fpath=(~/.config/zsh/functions $fpath)
autoload -Uz rehearsal-download rehearsal-finalize tex2chapters

# .zshrcを再読み込み
source ~/.zshrc

# 関数が存在するか確認
type rehearsal-download
```

### 2. 「Claude Code command not found」

**原因**: Claude Codeがインストールされていない

**解決**:
```bash
# Claude Codeをインストール
# https://claude.com/claude-code

# インストール後、確認
which claude
```

### 3. 「/rehearsal: No such command」

**原因**: Claude Codeコマンドがインストールされていない

**解決**:
```bash
# コマンドファイルが存在するか確認
ls -l ~/.claude/commands/rehearsal.md

# 存在しない場合、インストールスクリプトを再実行
cd rehearsal-workflow
./scripts/install.sh
```

### 4. 「Whisper処理が完了しない」

**原因**: リモートWhisperサーバーの問題

**確認**:
```bash
# Whisperプロセスが動作しているか確認
ps aux | grep whisper

# ログ確認
tail -f /path/to/whisper/log
```

### 5. 「PDF生成失敗」

**原因**: LuaLaTeXコンパイルエラー

**解決**:
```bash
# LaTeXファイルの構文確認
# ログファイルを確認
cat リハーサル記録.log

# 手動コンパイルテスト
luatex-pdf リハーサル記録.tex
```

---

## 開発情報

### ファイル構成

```
gui/
├── rehearsal_gui.py       # メインGUIアプリケーション (955行)
├── requirements.txt       # Python依存パッケージ
└── README.md             # このファイル
```

### コーディングスタイル

- **言語**: Python 3.8+
- **GUIフレームワーク**: PySide6 (Qt6)
- **データクラス**: `@dataclass` を使用
- **シグナル/スロット**: Qt6のシグナル/スロット機構
- **プロセス管理**: `QProcess` で外部コマンド実行

### カスタマイズ

#### デフォルト値の変更

`RehearsalMetadata` dataclassでデフォルト値を変更:

```python
@dataclass
class RehearsalMetadata:
    organization: str = "あなたの団体名"
    conductor: str = "あなたの指揮者名"
    author: str = "あなたの名前"
```

#### ログ色の変更

`LogViewer` クラスでログ色を変更:

```python
def log_info(self, message: str):
    self.append(f'<span style="color: #YOUR_COLOR;">[INFO]</span> {message}')
```

#### ファイル監視間隔の変更

`FileMonitorWidget.__init__` でタイマー間隔を変更:

```python
self.timer.start(5000)  # 5秒ごとに変更
```

---

## 既知の制限事項

1. **Step 2は手動実行**: Claude AIの対話型分析は自動化できないため、手動でClaude Codeを起動する必要がある
2. **カレントディレクトリ依存**: GUIはカレントディレクトリでファイルを検出するため、起動前に適切なディレクトリに移動する必要がある
3. **macOS/Linux専用**: Zsh関数に依存するため、Windowsでは動作しない（WSL経由なら可能）

---

## 今後の改善予定

- [ ] ファイルブラウザ機能（複数プロジェクトの管理）
- [ ] Whisper進行状況のリアルタイム表示（リモートサーバーAPI連携）
- [ ] PDFビューア統合
- [ ] チャプターエディタ
- [ ] YouTube自動アップロード機能（OAuth連携）
- [ ] 設定ファイル（YAML）でのバッチ処理

---

## ライセンス

このGUIは`rehearsal-workflow`プロジェクトの一部として、MITライセンスの下で配布されます。

---

## 関連リンク

- [rehearsal-workflow本体](../README.md)
- [インストールガイド](../docs/installation.md)
- [実装詳細](../docs/implementation.md)
- [Claude Code](https://claude.com/claude-code)
- [luatex-docker-remote](https://github.com/mashi727/luatex-docker-remote)
- [movie-viewer](https://github.com/mashi727/movie-viewer)

---

**作成者**: rehearsal-workflow contributors
**更新日**: 2025-11-06
**バージョン**: 1.0.0
