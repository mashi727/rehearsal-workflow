# リハーサル記録作成（Claude AI分析 + LaTeX生成）

オーケストラ・吹奏楽のリハーサル動画から作成された字幕ファイル（YouTube自動生成 + Whisper高精度文字起こし）を統合分析し、参加できなかったメンバーにも理解できるよう適切に構造化された詳細なリハーサル記録をLuaTeX形式で作成してください。

## 前提条件の確認（必須）

**重要**: レポート作成前に、以下の情報を必ず質問形式で確認してください：

1. **処理対象ファイル**:
   - YouTube自動生成字幕ファイル（`*_yt.srt`）のファイル名
   - Whisper高精度字幕ファイル（`*_wp.srt`）のファイル名
   - 両ファイルが存在することを確認

2. **リハーサル基本情報**:
   - 日付（YYYY年MM月DD日）
   - 団体名（例：創価大学 新世紀管弦楽団）
   - 指揮者名（敬称付き、例：阪本正彦先生）
   - 曲目（作曲家・曲名・作品番号）
   - 本番日程（例：2025年12月14日 定期演奏会）

3. **レポート作成者**:
   - 著者名（例：ホルン奏者有志、トランペット奏者有志）
   - 視点（例：ホルンセクションの視点、全体記録）

## 字幕ファイルの分析方針

### YouTube字幕（`*_yt.srt`）の特徴
- **長所**: 音楽演奏中も継続的に記録、動画全体をカバー
- **短所**: 精度が低い、誤認識が多い
- **用途**: 時系列構造の把握、演奏セクションの特定

### Whisper字幕（`*_wp.srt`）の特徴
- **長所**: 発話内容の精度が高い、指揮者の指示を正確に記録
- **短所**: 音楽演奏中は記録されない場合がある
- **用途**: 指揮者の具体的な指示内容、技術的アドバイス

### 統合分析アプローチ
1. **時系列構造**: YouTube字幕で全体の流れを把握
2. **詳細内容**: Whisper字幕で指揮者の指示を正確に記録
3. **相互補完**: 両方の長所を活かし、最も正確な記録を生成

## レポート生成要件

### 構造化

**必須セクション構成**:

1. **リハーサル概要**
   - 基本情報（日付、団体、指揮者、曲目、本番日程）
   - 時系列構造（全体の流れ、主要セクション）
   - データソース（使用した字幕ファイル、カバー範囲）

2. **時系列展開**（曲ごとまたは楽章ごと）
   - `\section{曲名・楽章 [開始時刻〜終了時刻]}`
   - `\subsection{練習セクション [HH:MM:SS.mmm]}`
   - `\subsubsection{具体的指示 [HH:MM:SS.mmm]}`
   - **重要**: すべてのセクションにタイムスタンプを付与

3. **パート別指示まとめ**
   - 著者のパート（例：ホルン）向けの指示を抽出
   - 重要度順に整理
   - タイムスタンプへの参照を含める

4. **音楽用語集**
   - リハーサルで使用されたイタリア語音楽用語
   - 日本語説明を付記

5. **擬音語パターン**（該当する場合）
   - 指揮者が使用したリズム・メロディーの口唱
   - 対応する楽譜上の箇所

6. **リハーサルの特徴と指揮者の教育スタイル**
   - 指揮者の指導方針、教育的アプローチ
   - リハーサルの雰囲気、特徴的な瞬間

7. **重要な瞬間**
   - リハーサル中の特に重要なシーン
   - タイムスタンプ付きで記録

8. **Summary（あと書き）**
   - リハーサル全体の総括
   - 本番に向けた課題と目標
   - **謝辞**: Claude Code氏への謝意を表明

### タイムスタンプの形式

**重要**: すべてのセクション・サブセクションにタイムスタンプを付与してください。

- **形式**: `[HH:MM:SS.mmm]`（ミリ秒3桁まで記録）
- **位置**: セクションタイトルの末尾
- **例**:
  ```latex
  \section{リハーサル概要 [00:00:06]}
  \subsection{冒頭部分の練習 [00:11:35.959]}
  \subsubsection{ホルン3番・4番への音色指導 [00:13:12.880]}
  ```

### 文脈からの補足と校正

**指揮者の指示を記録する際**:
- 発話内容だけでなく、音楽的文脈を補足
- 誤認識を文脈から修正（例：「ホルモン」→「ホルン」）
- 指示の対象パート、楽譜上の位置を明記
- 音楽用語は正確な表記に統一

**例**:
```
❌ 元の字幕: "ほるもんもっとおおきく"
✅ 校正後: ホルンはもっと大きく（フォルテで）
```

## LuaTeX出力仕様

### ドキュメントクラス
```latex
\documentclass[a4paper,10pt,twocolumn]{ltjsarticle}
```

### フォント設定

以下を**必ず**使用してください：

```latex
% LuaLaTeX用フォント設定パッケージ
\usepackage{luatexja-fontspec}
\usepackage{amsmath,amssymb}
\usepackage{unicode-math}  % Unicode数式フォント用

% ====================
% 欧文フォント設定 (Libertinus)
% ====================
\setmainfont{Libertinus Serif}[
    BoldFont = {Libertinus Serif Bold},
    ItalicFont = {Libertinus Serif Italic},
    BoldItalicFont = {Libertinus Serif Bold Italic}
]
\setsansfont{Libertinus Sans}[
    BoldFont = {Libertinus Sans Bold},
    ItalicFont = {Libertinus Sans Italic}
]
\setmonofont{Libertinus Mono}

% ====================
% 日本語フォント設定 (原ノ味フォント)
% ====================
\setmainjfont{HaranoAjiMincho-Regular}[
    BoldFont = {HaranoAjiGothic-Medium},
    ItalicFont = {HaranoAjiMincho-Regular},
    BoldItalicFont = {HaranoAjiGothic-Bold}
]
\setsansjfont{HaranoAjiGothic-Regular}[
    BoldFont = {HaranoAjiGothic-Bold}
]
% 原ノ味には専用の等幅フォントがないため、ゴシック体を使用
\setmonojfont{HaranoAjiGothic-Regular}

% ====================
% 数式フォント設定 (Libertinus Math)
% ====================
\setmathfont{Libertinus Math}
```

### JST日付・時刻表示

**重要**: ファイル生成時の日付と時刻をJST（日本標準時）で固定表示してください。

```latex
% ファイル生成日時（JST）
\newcommand{\generatedDate}{2025-11-05}  % ← 実際の生成日付に置換
\newcommand{\generatedTime}{14:30}       % ← 実際の生成時刻に置換

% ヘッダー・フッター設定
\usepackage{fancyhdr}
\usepackage{lastpage}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\small \generatedDate\ \generatedTime\ JST (\thepage/\pageref{LastPage})}
\renewcommand{\headrulewidth}{0.4pt}
```

### ハイパーリンクの設定

```latex
% その他のパッケージ
\usepackage[margin=20mm]{geometry}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{array}

% ハイパーリンクの色設定
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
    citecolor=blue
}
```

### タイトル・著者・日付

```latex
\title{【団体名】定期演奏会リハーサル記録\\
\large 曲名}
\author{著者名}
\date{}  % ← 必ず空にする
```

### その他の要件

- **目次**: `\tableofcontents` を含める
- **2段組**: `twocolumn` オプション使用
- **表**: linewidthをはみ出さないよう調整、縦線なし
- **余白**: 20mm（geometry設定済み）

## コンパイルコマンド

**重要**: LuaTeXファイルのコンパイルには必ず `luatex-pdf` コマンドを使用してください。

```bash
luatex-pdf リハーサル記録.tex
```

## 出力ファイル命名規則

```
YYYYMMDD_曲名_リハーサル記録.tex
```

**例**:
```
20251102_ドヴォルザーク交響曲第8番_リハーサル記録.tex
20251102_ロザムンデ・くるみ割り人形_リハーサル記録.tex
```

## 処理フロー

1. **前提条件の質問**（ファイル名、リハーサル情報、著者）
2. **字幕ファイルの読み込みと分析**
   - YouTube字幕で時系列構造を把握
   - Whisper字幕で指揮者の指示を抽出
3. **統合分析と構造化**
   - タイムスタンプ付きセクション構成
   - 指揮者の指示を文脈に沿って校正・補足
4. **LaTeXファイル生成**
   - 上記仕様に従って記述
   - ファイル保存
5. **コンパイル**（オプション）
   - `luatex-pdf` コマンドでPDF生成

## 音楽用語の取り扱い

リハーサルで頻出する用語:

- **イタリア語**: forte, piano, crescendo, diminuendo, legato, staccato, dolce, cantabile, espressivo
- **リハーサルマーク**: A, B, C...（大文字アルファベット）
- **小節番号**: 「43小節目」「練習番号Dから」
- **擬音語**: 「タンタタタ」「ラララ」（リズムやメロディーの口唱）
- **奏法**: スピッカート、デタシェ、ポルタメント

これらは正確な表記に統一し、必要に応じて日本語説明を付記してください。

## 品質基準

生成されたリハーサル記録は以下を満たすこと:

- ✅ 参加できなかったメンバーが読むだけで内容を理解できる
- ✅ 指揮者の指示が文脈と共に正確に記録されている
- ✅ タイムスタンプにより動画と対応づけられる
- ✅ 著者のパート（ホルンなど）向けの指示が明確に抽出されている
- ✅ 音楽的に意味のある構造化がされている
- ✅ LuaLaTeXで正常にコンパイルできる

## 次のステップ（ワークフロー統合）

このスラッシュコマンドは、以下のワークフローの一部です:

**ステップ1** (事前実行済み):
```bash
rehearsal-download "https://youtu.be/VIDEO_ID"
```
→ 動画ダウンロード + Whisper文字起こし起動

**ステップ2** (このコマンド):
```
claude code
/rehearsal
```
→ AI分析 + LaTeX生成

**ステップ3**:
```bash
rehearsal-finalize リハーサル記録.tex
```
→ PDF生成 + チャプター抽出

## 注意事項

- 字幕ファイルが非常に大きい場合（6000行以上）、分割読み込みを検討
- Whisper字幕がない場合でも、YouTube字幕のみで処理可能
- リハーサルマークや小節番号は字幕から正確に抽出
- 指揮者の発話の文脈を理解し、適切に補足・校正
