# Installation Guide

このガイドでは、Rehearsal Workflowのインストール手順を詳しく説明します。

## 前提条件

### オペレーティングシステム

- macOS 10.15以上
- Linux (Ubuntu 20.04以上、Debian、その他主要ディストリビューション)

### シェル

- **Zsh 5.0以上**（必須）

確認方法:
```bash
zsh --version
```

macOSではデフォルトでZshがインストールされています。

---

## 依存ツールのインストール

### 1. Claude Code

**Claude Code**は、Anthropic社のAI統合開発環境です。

インストール:
1. [claude.com/claude-code](https://claude.com/claude-code) にアクセス
2. アカウントを作成またはログイン
3. 指示に従ってClaude Codeをインストール

確認:
```bash
claude --version
```

### 2. luatex-pdf (LuaLaTeXリモートコンパイラ)

**luatex-pdf**は、リモートサーバー上のDockerコンテナでLuaLaTeXをコンパイルするツールです。ローカル環境を汚さず、強力なリモートリソースを活用できます。

#### セットアップ手順

1. **リポジトリのクローン**:
   ```bash
   git clone https://github.com/mashi727/luatex-docker-remote.git
   cd luatex-docker-remote
   ```

2. **インストール**:
   ```bash
   make install
   ```

3. **ネットワーク自動検出の設定** (内部/外部ホスト自動切り替え):
   ```bash
   make setup-network
   ```

4. **設定を反映**:
   ```bash
   source ~/.bashrc  # または ~/.zshrc
   ```

5. **動作確認**:
   ```bash
   luatex-pdf --help
   ```

#### 必要な環境

- **SSHアクセス**: リモートサーバーへのSSH接続
- **rsync**: ファイル同期（通常は標準インストール済み）
- **リモートサーバー**: Dockerが動作するサーバー

詳細: [luatex-docker-remote README](https://github.com/mashi727/luatex-docker-remote)

#### 動作原理

`luatex-pdf`は以下の4段階で動作します:

1. **同期**: ローカルの.texファイルとスタイルファイルをリモートに転送
2. **コンパイル**: リモートDockerコンテナ内でLuaLaTeXを実行
3. **取得**: 生成されたPDFをローカルに転送
4. **クリーンアップ**: リモートの一時ファイルを削除

### 3. ytdl (YouTube動画ダウンロード)

**ytdl**は、YouTube動画と字幕をダウンロードするツール（ytdl-claude関数）です。

> **Note**: このツールの具体的なインストール方法については、プロジェクト管理者にお問い合わせください。

確認:
```bash
ytdl --help
```

### 4. whisper-remote (Whisper文字起こし)

**whisper-remote**は、リモートGPUサーバーでWhisperによる高精度文字起こしを実行するツールです。

> **Note**: このツールの具体的なインストール方法については、プロジェクト管理者にお問い合わせください。

確認:
```bash
whisper-remote --help
```

---

## Rehearsal Workflowのインストール

### ステップ1: リポジトリのクローン

```bash
git clone https://github.com/mashi727/rehearsal-workflow.git
cd rehearsal-workflow
```

### ステップ2: インストールスクリプトの実行

```bash
./scripts/install.sh
```

インストールスクリプトは以下を実行します:

1. **依存関係チェック**: 必要なツールがインストールされているか確認
2. **Zsh関数のインストール**: `~/.config/zsh/functions/`にコピー
3. **Claude Codeコマンドのインストール**: `~/.claude/commands/`にコピー
4. **`.zshrc`設定の追加**: 自動または手動で追加

### ステップ3: Zsh設定の反映

```bash
source ~/.zshrc
```

### ステップ4: 動作確認

```bash
# 各関数が利用可能か確認
type rehearsal-download
type rehearsal-finalize
type tex2chapters

# Claude Codeコマンドの確認
ls ~/.claude/commands/rehearsal.md
```

すべて正常に表示されれば、インストール完了です！

---

## オプションツールのインストール

### pdfinfo (PDF情報表示)

`rehearsal-finalize`がPDFのページ数を表示するために使用します。

**macOS** (Homebrew):
```bash
brew install poppler
```

**Ubuntu/Debian**:
```bash
sudo apt-get install poppler-utils
```

確認:
```bash
pdfinfo -v
```

### GitHub CLI (gh)

リポジトリ管理やIssue作成に便利です。

**macOS**:
```bash
brew install gh
gh auth login
```

**Ubuntu/Debian**:
```bash
sudo apt-get install gh
gh auth login
```

---

## フォントのインストール

LuaLaTeX PDFコンパイルには以下のフォントが必要です。リモートサーバー側にインストールされている必要があります。

### Libertinus (欧文フォント)

**macOS**:
```bash
brew install --cask font-libertinus
```

**Linux**:
```bash
# ダウンロード
wget https://github.com/alerque/libertinus/releases/download/v7.040/Libertinus-7.040.tar.xz
tar -xf Libertinus-7.040.tar.xz
sudo mkdir -p /usr/share/fonts/truetype/libertinus
sudo cp Libertinus-7.040/static/OTF/*.otf /usr/share/fonts/truetype/libertinus/
sudo fc-cache -fv
```

### 原ノ味 (日本語フォント)

**macOS**:
```bash
brew install --cask font-harano-aji
```

**Linux**:
```bash
# ダウンロード
wget https://github.com/trueroad/HaranoAjiFonts/releases/download/20231009/HaranoAjiFonts-20231009.zip
unzip HaranoAjiFonts-20231009.zip
sudo mkdir -p /usr/share/fonts/opentype/haranoaji
sudo cp HaranoAjiFonts-20231009/*.otf /usr/share/fonts/opentype/haranoaji/
sudo fc-cache -fv
```

確認:
```bash
fc-list | grep -i libertinus
fc-list | grep -i harano
```

---

## トラブルシューティング

### 関数が見つからない

```bash
# fpath の確認
echo $fpath | grep ".config/zsh/functions"

# 出力がない場合、.zshrcに以下を追加:
fpath=(~/.config/zsh/functions $fpath)

# 関数の明示的な読み込み
autoload -Uz rehearsal-download rehearsal-finalize tex2chapters

# 設定を反映
source ~/.zshrc
```

### luatex-pdfが動作しない

1. **SSHアクセスの確認**:
   ```bash
   ssh your-remote-server
   ```

2. **ネットワーク検出の再設定**:
   ```bash
   cd luatex-docker-remote
   make setup-network
   ```

3. **手動テスト**:
   ```bash
   echo "\\documentclass{article}\\begin{document}Hello\\end{document}" > test.tex
   luatex-pdf test.tex
   ```

### ytdl-claudeまたはwhisper-remoteが動作しない

これらのツールはプロジェクト固有のため、セットアップ方法について管理者にお問い合わせください。

---

## アンインストール

Rehearsal Workflowをアンインストールする場合:

```bash
# Zsh関数の削除
rm ~/.config/zsh/functions/rehearsal-download
rm ~/.config/zsh/functions/rehearsal-finalize
rm ~/.config/zsh/functions/tex2chapters

# Claude Codeコマンドの削除
rm ~/.claude/commands/rehearsal.md

# .zshrcから設定を削除（手動）
# 以下の行を削除:
# fpath=(~/.config/zsh/functions $fpath)
# autoload -Uz tex2chapters rehearsal-download rehearsal-finalize
```

---

## 次のステップ

インストールが完了したら、[Usage Guide](usage.md)で使い方を学びましょう！

簡単なクイックスタート:

```bash
# ステップ1: ダウンロード
rehearsal-download "https://youtu.be/VIDEO_ID"

# ステップ2: AI分析（Whisper完了後）
claude code
/rehearsal

# ステップ3: PDF生成
rehearsal-finalize "リハーサル記録.tex"
```
