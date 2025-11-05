#!/usr/bin/env python3
"""
rehearsal_gui.py - Rehearsal Workflow GUI

リハーサル記録作成ワークフローのグラフィカルフロントエンド。
YouTube動画URLから最終PDF・チャプター生成までの3ステップを可視化・実行。

ワークフロー:
  1. YouTube動画ダウンロード + Whisper文字起こし起動 (rehearsal-download)
  2. AI分析 + LaTeX生成 (Claude Code /rehearsal)
  3. PDF生成 + チャプター抽出 (rehearsal-finalize)

依存:
  - PySide6 (Qt for Python)
  - rehearsal-workflow (zsh functions + Claude command)
  - Claude Code (AI分析エンジン)

使用方法:
  python3 rehearsal_gui.py

作成日: 2025-11-06
バージョン: 1.0.0
"""

import sys
import os
import subprocess
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
from enum import Enum

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFileDialog,
    QComboBox, QCheckBox, QProgressBar, QTabWidget, QScrollArea,
    QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QProcess, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette


# ==============================================================================
# 定数
# ==============================================================================

# 設定ファイルのパス（ホームディレクトリ）
CONFIG_FILE = Path.home() / ".config" / "rehearsal-workflow" / "settings.yaml"


# ==============================================================================
# データモデル
# ==============================================================================

class WorkflowStep(Enum):
    """ワークフロー進行状況"""
    IDLE = 0
    DOWNLOADING = 1
    WAITING_WHISPER = 2
    ANALYZING = 3
    FINALIZING = 4
    COMPLETED = 5
    ERROR = -1


@dataclass
class RehearsalMetadata:
    """リハーサル記録メタデータ"""
    # 必須情報
    youtube_url: str = ""
    rehearsal_date: str = ""  # YYYY-MM-DD
    organization: str = "創価大学 新世紀管弦楽団"
    conductor: str = "阪本正彦先生"
    piece_name: str = ""
    concert_date: str = ""  # YYYY-MM-DD
    author: str = "ホルン奏者有志"

    # ファイル情報（自動検出）
    video_file: str = ""
    yt_srt_file: str = ""
    wp_srt_file: str = ""
    tex_file: str = ""
    pdf_file: str = ""
    youtube_chapters: str = ""
    movieviewer_chapters: str = ""

    # ワークフロー状態
    step: WorkflowStep = WorkflowStep.IDLE
    step_message: str = ""

    # Whisper設定
    use_demucs: bool = True  # 音源分離（音楽が大きい場合）

    # 生成時刻（JST）
    generation_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    generation_time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))

    def to_dict(self):
        """設定保存用の辞書に変換（保存不要なフィールドを除外）"""
        data = asdict(self)
        # ファイル情報とワークフロー状態は保存しない
        exclude_keys = [
            'video_file', 'yt_srt_file', 'wp_srt_file',
            'tex_file', 'pdf_file', 'youtube_chapters', 'movieviewer_chapters',
            'step', 'step_message', 'generation_date', 'generation_time'
        ]
        for key in exclude_keys:
            data.pop(key, None)
        return data

    @classmethod
    def from_dict(cls, data: dict):
        """辞書から復元"""
        # stepはEnumなので特別に処理
        if 'step' in data and isinstance(data['step'], int):
            data['step'] = WorkflowStep(data['step'])
        # 存在しないキーは無視
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


# ==============================================================================
# 設定管理
# ==============================================================================

def save_settings(metadata: RehearsalMetadata):
    """設定をYAMLファイルに保存"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(metadata.to_dict(), f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def load_settings() -> Optional[RehearsalMetadata]:
    """設定をYAMLファイルから読み込み"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    return RehearsalMetadata.from_dict(data)
    except Exception as e:
        print(f"Error loading settings: {e}")
    return None


# ==============================================================================
# UI コンポーネント
# ==============================================================================

class LogViewer(QTextEdit):
    """リアルタイムログ表示ウィジェット"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Monaco", 18))

        # ダークテーマ風スタイル
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                padding: 8px;
                font-size: 18pt;
            }
        """)

    def log_info(self, message: str):
        """情報ログ（緑）"""
        self.append(f'<span style="color: #4ec9b0;">[INFO]</span> {message}')

    def log_warn(self, message: str):
        """警告ログ（黄）"""
        self.append(f'<span style="color: #dcdcaa;">[WARN]</span> {message}')

    def log_error(self, message: str):
        """エラーログ（赤）"""
        self.append(f'<span style="color: #f48771;">[ERROR]</span> {message}')

    def log_step(self, message: str):
        """ステップログ（青）"""
        self.append(f'<span style="color: #569cd6;">[STEP]</span> {message}')

    def log_success(self, message: str):
        """成功ログ（明るい緑）"""
        self.append(f'<span style="color: #6a9955;">[SUCCESS]</span> {message}')


class MetadataInputWidget(QWidget):
    """リハーサル基本情報入力ウィジェット"""

    def __init__(self, metadata: RehearsalMetadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.init_ui()

    def update_and_save(self, field: str, value):
        """フィールドを更新して自動保存"""
        setattr(self.metadata, field, value)
        save_settings(self.metadata)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # フォント設定
        font = QFont()
        font.setPointSize(18)

        # YouTube URL（必須）
        url_group = QGroupBox("YouTube動画URL（必須）")
        url_group.setFont(font)
        url_layout = QVBoxLayout()
        self.url_input = QLineEdit(self.metadata.youtube_url)
        self.url_input.setFont(font)
        self.url_input.setPlaceholderText("https://youtu.be/VIDEO_ID")
        self.url_input.textChanged.connect(lambda text: self.update_and_save('youtube_url', text))
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # リハーサル情報
        info_group = QGroupBox("リハーサル基本情報")
        info_group.setFont(font)
        info_layout = QVBoxLayout()

        # 日付
        date_layout = QHBoxLayout()
        date_label = QLabel("リハーサル日付:")
        date_label.setFont(font)
        date_layout.addWidget(date_label)
        self.date_input = QLineEdit(self.metadata.rehearsal_date)
        self.date_input.setFont(font)
        self.date_input.setPlaceholderText("YYYY-MM-DD")
        self.date_input.textChanged.connect(lambda text: self.update_and_save('rehearsal_date', text))
        date_layout.addWidget(self.date_input)
        info_layout.addLayout(date_layout)

        # 団体名
        org_layout = QHBoxLayout()
        org_label = QLabel("団体名:")
        org_label.setFont(font)
        org_layout.addWidget(org_label)
        self.org_input = QLineEdit(self.metadata.organization)
        self.org_input.setFont(font)
        self.org_input.textChanged.connect(lambda text: self.update_and_save('organization', text))
        org_layout.addWidget(self.org_input)
        info_layout.addLayout(org_layout)

        # 指揮者
        conductor_layout = QHBoxLayout()
        conductor_label = QLabel("指揮者:")
        conductor_label.setFont(font)
        conductor_layout.addWidget(conductor_label)
        self.conductor_input = QLineEdit(self.metadata.conductor)
        self.conductor_input.setFont(font)
        self.conductor_input.textChanged.connect(lambda text: self.update_and_save('conductor', text))
        conductor_layout.addWidget(self.conductor_input)
        info_layout.addLayout(conductor_layout)

        # 曲名
        piece_layout = QHBoxLayout()
        piece_label = QLabel("曲名:")
        piece_label.setFont(font)
        piece_layout.addWidget(piece_label)
        self.piece_input = QLineEdit(self.metadata.piece_name)
        self.piece_input.setFont(font)
        self.piece_input.setPlaceholderText("例: ドヴォルザーク交響曲第8番")
        self.piece_input.textChanged.connect(lambda text: self.update_and_save('piece_name', text))
        piece_layout.addWidget(self.piece_input)
        info_layout.addLayout(piece_layout)

        # 本番日程
        concert_layout = QHBoxLayout()
        concert_label = QLabel("本番日程:")
        concert_label.setFont(font)
        concert_layout.addWidget(concert_label)
        self.concert_input = QLineEdit(self.metadata.concert_date)
        self.concert_input.setFont(font)
        self.concert_input.setPlaceholderText("YYYY-MM-DD")
        self.concert_input.textChanged.connect(lambda text: self.update_and_save('concert_date', text))
        concert_layout.addWidget(self.concert_input)
        info_layout.addLayout(concert_layout)

        # 著者
        author_layout = QHBoxLayout()
        author_label = QLabel("著者:")
        author_label.setFont(font)
        author_layout.addWidget(author_label)
        self.author_input = QLineEdit(self.metadata.author)
        self.author_input.setFont(font)
        self.author_input.textChanged.connect(lambda text: self.update_and_save('author', text))
        author_layout.addWidget(self.author_input)
        info_layout.addLayout(author_layout)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Whisper設定
        whisper_group = QGroupBox("Whisper文字起こし設定")
        whisper_group.setFont(font)
        whisper_layout = QVBoxLayout()
        self.demucs_checkbox = QCheckBox("音源分離を使用（Demucs）")
        self.demucs_checkbox.setFont(font)
        self.demucs_checkbox.setChecked(self.metadata.use_demucs)
        self.demucs_checkbox.setToolTip("音楽が大きい場合、音声と音楽を分離して文字起こし精度を向上")
        self.demucs_checkbox.stateChanged.connect(
            lambda state: self.update_and_save('use_demucs', state == Qt.CheckState.Checked)
        )
        whisper_layout.addWidget(self.demucs_checkbox)
        whisper_group.setLayout(whisper_layout)
        layout.addWidget(whisper_group)

        # 設定保存・読み込みボタン
        button_layout = QHBoxLayout()

        save_button = QPushButton("💾 設定を保存")
        save_button.setFont(font)
        save_button.setStyleSheet("QPushButton { font-size: 18pt; padding: 10px; background-color: #4CAF50; color: white; }")
        save_button.clicked.connect(self.save_settings_manually)
        button_layout.addWidget(save_button)

        load_button = QPushButton("📂 設定を読み込み")
        load_button.setFont(font)
        load_button.setStyleSheet("QPushButton { font-size: 18pt; padding: 10px; background-color: #2196F3; color: white; }")
        load_button.clicked.connect(self.load_settings_manually)
        button_layout.addWidget(load_button)

        layout.addLayout(button_layout)

        # 設定ファイルパス表示
        config_label = QLabel(f"設定ファイル: {CONFIG_FILE}")
        config_label.setFont(QFont("Arial", 12))
        config_label.setStyleSheet("QLabel { color: #888; }")
        layout.addWidget(config_label)

        layout.addStretch()

    def save_settings_manually(self):
        """手動で設定を保存"""
        if save_settings(self.metadata):
            QMessageBox.information(self, "保存完了", f"設定を保存しました。\n\n{CONFIG_FILE}")
        else:
            QMessageBox.warning(self, "保存失敗", "設定の保存に失敗しました。")

    def load_settings_manually(self):
        """手動で設定を読み込み"""
        loaded_metadata = load_settings()
        if loaded_metadata:
            # 各フィールドを更新
            self.url_input.setText(loaded_metadata.youtube_url)
            self.date_input.setText(loaded_metadata.rehearsal_date)
            self.org_input.setText(loaded_metadata.organization)
            self.conductor_input.setText(loaded_metadata.conductor)
            self.piece_input.setText(loaded_metadata.piece_name)
            self.concert_input.setText(loaded_metadata.concert_date)
            self.author_input.setText(loaded_metadata.author)
            self.demucs_checkbox.setChecked(loaded_metadata.use_demucs)

            QMessageBox.information(self, "読み込み完了", f"設定を読み込みました。\n\n{CONFIG_FILE}")
        else:
            QMessageBox.warning(self, "読み込み失敗", "設定ファイルが見つかりませんでした。")


class WorkflowControlWidget(QWidget):
    """ワークフロー制御ウィジェット"""

    # シグナル
    step1_clicked = Signal()
    step2_clicked = Signal()
    step3_clicked = Signal()

    def __init__(self, metadata: RehearsalMetadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # フォント設定
        font = QFont()
        font.setPointSize(18)

        # ステップ1: ダウンロード + Whisper
        step1_group = QGroupBox("Step 1: YouTube動画ダウンロード + Whisper文字起こし")
        step1_group.setFont(font)
        step1_layout = QVBoxLayout()

        self.step1_button = QPushButton("📥 ダウンロード開始（rehearsal-download）")
        self.step1_button.setStyleSheet("QPushButton { font-size: 18pt; padding: 10px; }")
        self.step1_button.clicked.connect(self.step1_clicked.emit)
        step1_layout.addWidget(self.step1_button)

        self.step1_status = QLabel("待機中")
        self.step1_status.setFont(font)
        self.step1_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step1_layout.addWidget(self.step1_status)

        step1_group.setLayout(step1_layout)
        layout.addWidget(step1_group)

        # ステップ2: Claude AI分析
        step2_group = QGroupBox("Step 2: AI分析 + LaTeX生成")
        step2_group.setFont(font)
        step2_layout = QVBoxLayout()

        step2_info = QLabel("⚠️ このステップはClaude Codeで手動実行:\n"
                           "1. ターミナルで「claude code」を実行\n"
                           "2. 「/rehearsal」コマンドを入力\n"
                           "3. 質問に回答してLaTeXファイルを生成")
        step2_info.setFont(font)
        step2_info.setWordWrap(True)
        step2_info.setStyleSheet("QLabel { color: #dcdcaa; font-size: 18pt; }")
        step2_layout.addWidget(step2_info)

        self.step2_button = QPushButton("✅ ステップ2完了（LaTeXファイル選択）")
        self.step2_button.setStyleSheet("QPushButton { font-size: 18pt; padding: 10px; }")
        self.step2_button.clicked.connect(self.step2_clicked.emit)
        self.step2_button.setEnabled(False)
        step2_layout.addWidget(self.step2_button)

        self.step2_status = QLabel("待機中（Step 1完了後）")
        self.step2_status.setFont(font)
        self.step2_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step2_layout.addWidget(self.step2_status)

        step2_group.setLayout(step2_layout)
        layout.addWidget(step2_group)

        # ステップ3: PDF + チャプター生成
        step3_group = QGroupBox("Step 3: PDF生成 + チャプター抽出")
        step3_group.setFont(font)
        step3_layout = QVBoxLayout()

        self.step3_button = QPushButton("📄 PDF生成開始（rehearsal-finalize）")
        self.step3_button.setStyleSheet("QPushButton { font-size: 18pt; padding: 10px; }")
        self.step3_button.clicked.connect(self.step3_clicked.emit)
        self.step3_button.setEnabled(False)
        step3_layout.addWidget(self.step3_button)

        self.step3_status = QLabel("待機中（Step 2完了後）")
        self.step3_status.setFont(font)
        self.step3_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step3_layout.addWidget(self.step3_status)

        step3_group.setLayout(step3_layout)
        layout.addWidget(step3_group)

        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(font)
        self.progress_bar.setRange(0, 3)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

    def update_step1_status(self, status: str, enable_step2: bool = False):
        """Step 1ステータス更新"""
        self.step1_status.setText(status)
        self.progress_bar.setValue(1)
        if enable_step2:
            self.step2_button.setEnabled(True)
            self.step2_status.setText("準備完了（Claude Codeを起動してください）")

    def update_step2_status(self, status: str, enable_step3: bool = False):
        """Step 2ステータス更新"""
        self.step2_status.setText(status)
        self.progress_bar.setValue(2)
        if enable_step3:
            self.step3_button.setEnabled(True)
            self.step3_status.setText("準備完了")

    def update_step3_status(self, status: str, completed: bool = False):
        """Step 3ステータス更新"""
        self.step3_status.setText(status)
        if completed:
            self.progress_bar.setValue(3)


class FileMonitorWidget(QWidget):
    """生成ファイルモニタリングウィジェット"""

    def __init__(self, metadata: RehearsalMetadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.init_ui()

        # 定期的にファイル存在チェック
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_files)
        self.timer.start(2000)  # 2秒ごと

    def init_ui(self):
        layout = QVBoxLayout(self)

        # フォント設定
        font = QFont()
        font.setPointSize(18)

        group = QGroupBox("生成ファイル")
        group.setFont(font)
        file_layout = QVBoxLayout()

        # ファイル一覧
        self.file_labels = {
            'video': QLabel("❌ 動画ファイル: 未検出"),
            'yt_srt': QLabel("❌ YouTube字幕: 未検出"),
            'wp_srt': QLabel("❌ Whisper字幕: 未検出"),
            'tex': QLabel("❌ LaTeXファイル: 未検出"),
            'pdf': QLabel("❌ PDFファイル: 未検出"),
            'youtube_ch': QLabel("❌ YouTubeチャプター: 未検出"),
            'mv_ch': QLabel("❌ Movie Viewerチャプター: 未検出"),
        }

        for label in self.file_labels.values():
            label.setFont(font)
            label.setWordWrap(True)
            file_layout.addWidget(label)

        group.setLayout(file_layout)
        layout.addWidget(group)

    def check_files(self):
        """ファイル存在チェック"""
        cwd = Path.cwd()

        # 動画ファイル（最新のmp4）
        video_files = sorted(cwd.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if video_files and not self.metadata.video_file:
            self.metadata.video_file = str(video_files[0].name)
            self.file_labels['video'].setText(f"✅ 動画ファイル: {video_files[0].name}")

        # YouTube字幕
        if self.metadata.video_file:
            basename = Path(self.metadata.video_file).stem
            yt_srt = cwd / f"{basename}_yt.srt"
            if yt_srt.exists():
                self.metadata.yt_srt_file = str(yt_srt.name)
                self.file_labels['yt_srt'].setText(f"✅ YouTube字幕: {yt_srt.name}")

        # Whisper字幕
        if self.metadata.video_file:
            basename = Path(self.metadata.video_file).stem
            wp_srt = cwd / f"{basename}_wp.srt"
            if wp_srt.exists():
                self.metadata.wp_srt_file = str(wp_srt.name)
                self.file_labels['wp_srt'].setText(f"✅ Whisper字幕: {wp_srt.name}")

        # LaTeXファイル
        tex_files = sorted(cwd.glob("*リハーサル記録.tex"), key=lambda p: p.stat().st_mtime, reverse=True)
        if tex_files:
            self.metadata.tex_file = str(tex_files[0].name)
            self.file_labels['tex'].setText(f"✅ LaTeXファイル: {tex_files[0].name}")

        # PDFファイル
        if self.metadata.tex_file:
            pdf_file = cwd / self.metadata.tex_file.replace('.tex', '.pdf')
            if pdf_file.exists():
                self.metadata.pdf_file = str(pdf_file.name)
                self.file_labels['pdf'].setText(f"✅ PDFファイル: {pdf_file.name}")

        # YouTubeチャプター
        if self.metadata.tex_file:
            youtube_ch = cwd / self.metadata.tex_file.replace('.tex', '_youtube.txt')
            if youtube_ch.exists():
                self.metadata.youtube_chapters = str(youtube_ch.name)
                self.file_labels['youtube_ch'].setText(f"✅ YouTubeチャプター: {youtube_ch.name}")

        # Movie Viewerチャプター
        if self.metadata.tex_file:
            mv_ch = cwd / self.metadata.tex_file.replace('.tex', '_movieviewer.txt')
            if mv_ch.exists():
                self.metadata.movieviewer_chapters = str(mv_ch.name)
                self.file_labels['mv_ch'].setText(f"✅ Movie Viewerチャプター: {mv_ch.name}")


# ==============================================================================
# メインウィンドウ
# ==============================================================================

class RehearsalWorkflowGUI(QMainWindow):
    """リハーサルワークフローGUIメインウィンドウ"""

    def __init__(self):
        super().__init__()

        # 設定を読み込み（存在すれば）
        loaded_metadata = load_settings()
        if loaded_metadata:
            self.metadata = loaded_metadata
            print(f"Settings loaded from: {CONFIG_FILE}")
        else:
            self.metadata = RehearsalMetadata()
            print("No saved settings found. Using defaults.")

        self.processes: List[QProcess] = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rehearsal Workflow GUI - リハーサル記録作成")
        self.setGeometry(100, 100, 1400, 900)

        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # メインレイアウト（左右分割）
        main_layout = QHBoxLayout(main_widget)

        # 左側: 入力・制御
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # タブウィジェット
        tabs = QTabWidget()
        tab_font = QFont()
        tab_font.setPointSize(18)
        tabs.setFont(tab_font)

        # タブ1: 基本情報
        self.metadata_widget = MetadataInputWidget(self.metadata)
        scroll_area1 = QScrollArea()
        scroll_area1.setWidget(self.metadata_widget)
        scroll_area1.setWidgetResizable(True)
        tabs.addTab(scroll_area1, "📝 基本情報")

        # タブ2: ワークフロー制御
        self.workflow_widget = WorkflowControlWidget(self.metadata)
        self.workflow_widget.step1_clicked.connect(self.execute_step1)
        self.workflow_widget.step2_clicked.connect(self.execute_step2)
        self.workflow_widget.step3_clicked.connect(self.execute_step3)
        scroll_area2 = QScrollArea()
        scroll_area2.setWidget(self.workflow_widget)
        scroll_area2.setWidgetResizable(True)
        tabs.addTab(scroll_area2, "🔄 ワークフロー")

        # タブ3: ファイルモニター
        self.file_monitor_widget = FileMonitorWidget(self.metadata)
        scroll_area3 = QScrollArea()
        scroll_area3.setWidget(self.file_monitor_widget)
        scroll_area3.setWidgetResizable(True)
        tabs.addTab(scroll_area3, "📁 生成ファイル")

        left_layout.addWidget(tabs)

        # 右側: ログビューア
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        log_label = QLabel("実行ログ")
        log_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        right_layout.addWidget(log_label)

        self.log_viewer = LogViewer()
        right_layout.addWidget(self.log_viewer)

        # 左右分割
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 800])

        main_layout.addWidget(splitter)

        # 初期メッセージ
        self.log_viewer.log_info("Rehearsal Workflow GUI 起動")
        self.log_viewer.log_info("カレントディレクトリ: " + str(Path.cwd()))
        self.log_viewer.log_step("Step 1から開始してください")

    def execute_step1(self):
        """Step 1: YouTube動画ダウンロード + Whisper起動"""
        if not self.metadata.youtube_url:
            QMessageBox.warning(self, "入力エラー", "YouTube URLを入力してください")
            return

        self.log_viewer.log_step("Step 1: YouTube動画ダウンロード + Whisper起動")
        self.log_viewer.log_info(f"URL: {self.metadata.youtube_url}")

        # rehearsal-download実行
        cmd = ["rehearsal-download", self.metadata.youtube_url]

        self.log_viewer.log_info(f"実行: {' '.join(cmd)}")
        self.workflow_widget.step1_button.setEnabled(False)
        self.workflow_widget.step1_status.setText("実行中...")

        # プロセス起動
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        process.readyReadStandardOutput.connect(
            lambda: self.handle_process_output(process)
        )
        process.finished.connect(
            lambda exit_code, exit_status: self.handle_step1_finished(exit_code, exit_status)
        )

        # Zshシェルで実行（関数が利用可能な環境）
        # .zshenvでパス設定、ytdl/whisper-remote関数source、fpathとautoloadを手動設定
        full_cmd = (
            f"source ~/.config/zsh/.zshenv && "
            f"source ~/.config/zsh/functions/ytdl-claude.zsh && "
            f"source ~/.config/zsh/functions/whisper-remote.zsh && "
            f"fpath=(~/.config/zsh/functions $fpath) && "
            f"autoload -Uz rehearsal-download rehearsal-finalize tex2chapters && "
            f"{' '.join(cmd)}"
        )
        process.start("zsh", ["-c", full_cmd])

        self.processes.append(process)

    def handle_process_output(self, process: QProcess):
        """プロセス出力処理"""
        output = process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        for line in output.strip().split('\n'):
            if line:
                # ANSIカラーコード除去
                import re
                line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line)

                if '[INFO]' in line_clean:
                    self.log_viewer.log_info(line_clean.replace('[INFO]', '').strip())
                elif '[WARN]' in line_clean:
                    self.log_viewer.log_warn(line_clean.replace('[WARN]', '').strip())
                elif '[ERROR]' in line_clean:
                    self.log_viewer.log_error(line_clean.replace('[ERROR]', '').strip())
                elif '[STEP]' in line_clean:
                    self.log_viewer.log_step(line_clean.replace('[STEP]', '').strip())
                elif '[SUCCESS]' in line_clean:
                    self.log_viewer.log_success(line_clean.replace('[SUCCESS]', '').strip())
                else:
                    self.log_viewer.append(line_clean)

    def handle_step1_finished(self, exit_code: int, exit_status):
        """Step 1完了処理"""
        if exit_code == 0:
            self.log_viewer.log_success("Step 1完了")
            self.log_viewer.log_info("Whisperが起動しました。完了するまで30分〜2時間かかります")
            self.log_viewer.log_step("Whisper完了後、Step 2に進んでください")
            self.workflow_widget.update_step1_status("完了（Whisper処理中...）", enable_step2=True)
        else:
            self.log_viewer.log_error(f"Step 1失敗（終了コード: {exit_code}）")
            self.workflow_widget.step1_button.setEnabled(True)
            self.workflow_widget.step1_status.setText("エラー発生")

    def execute_step2(self):
        """Step 2: LaTeXファイル選択"""
        self.log_viewer.log_step("Step 2: LaTeXファイル選択")
        self.log_viewer.log_info("Claude Codeで生成されたLaTeXファイルを選択してください")

        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "LaTeXファイルを選択",
            str(Path.cwd()),
            "LaTeX Files (*.tex)"
        )

        if file_path:
            self.metadata.tex_file = Path(file_path).name
            self.log_viewer.log_success(f"選択: {self.metadata.tex_file}")
            self.workflow_widget.update_step2_status("完了", enable_step3=True)
            self.log_viewer.log_step("Step 3に進んでください")
        else:
            self.log_viewer.log_warn("ファイルが選択されませんでした")

    def execute_step3(self):
        """Step 3: PDF生成 + チャプター抽出"""
        if not self.metadata.tex_file:
            QMessageBox.warning(self, "エラー", "LaTeXファイルが選択されていません")
            return

        self.log_viewer.log_step("Step 3: PDF生成 + チャプター抽出")
        self.log_viewer.log_info(f"ファイル: {self.metadata.tex_file}")

        # rehearsal-finalize実行
        cmd = ["rehearsal-finalize", self.metadata.tex_file]

        self.log_viewer.log_info(f"実行: {' '.join(cmd)}")
        self.workflow_widget.step3_button.setEnabled(False)
        self.workflow_widget.step3_status.setText("実行中...")

        # プロセス起動
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        process.readyReadStandardOutput.connect(
            lambda: self.handle_process_output(process)
        )
        process.finished.connect(
            lambda exit_code, exit_status: self.handle_step3_finished(exit_code, exit_status)
        )

        # Zshシェルで実行（関数が利用可能な環境）
        # .zshenvでパス設定、ytdl/whisper-remote関数source、fpathとautoloadを手動設定
        full_cmd = (
            f"source ~/.config/zsh/.zshenv && "
            f"source ~/.config/zsh/functions/ytdl-claude.zsh && "
            f"source ~/.config/zsh/functions/whisper-remote.zsh && "
            f"fpath=(~/.config/zsh/functions $fpath) && "
            f"autoload -Uz rehearsal-download rehearsal-finalize tex2chapters && "
            f"{' '.join(cmd)}"
        )
        process.start("zsh", ["-c", full_cmd])

        self.processes.append(process)

    def handle_step3_finished(self, exit_code: int, exit_status):
        """Step 3完了処理"""
        if exit_code == 0:
            self.log_viewer.log_success("Step 3完了")
            self.log_viewer.log_success("✅ ワークフロー完了！")
            self.log_viewer.log_info("")
            self.log_viewer.log_info("生成ファイル:")
            if self.metadata.pdf_file:
                self.log_viewer.log_info(f"  - PDF: {self.metadata.pdf_file}")
            if self.metadata.youtube_chapters:
                self.log_viewer.log_info(f"  - YouTubeチャプター: {self.metadata.youtube_chapters}")
            if self.metadata.movieviewer_chapters:
                self.log_viewer.log_info(f"  - Movie Viewerチャプター: {self.metadata.movieviewer_chapters}")

            self.workflow_widget.update_step3_status("完了", completed=True)

            # 完了ダイアログ
            QMessageBox.information(
                self,
                "ワークフロー完了",
                f"リハーサル記録の作成が完了しました。\n\n"
                f"PDF: {self.metadata.pdf_file}\n"
                f"YouTubeチャプター: {self.metadata.youtube_chapters}\n"
                f"Movie Viewerチャプター: {self.metadata.movieviewer_chapters}"
            )
        else:
            self.log_viewer.log_error(f"Step 3失敗（終了コード: {exit_code}）")
            self.workflow_widget.step3_button.setEnabled(True)
            self.workflow_widget.step3_status.setText("エラー発生")

    def closeEvent(self, event):
        """ウィンドウクローズ時の処理"""
        # 実行中のプロセスを終了
        for process in self.processes:
            if process.state() == QProcess.ProcessState.Running:
                process.terminate()
                process.waitForFinished(3000)

        event.accept()


# ==============================================================================
# エントリーポイント
# ==============================================================================

def main():
    app = QApplication(sys.argv)

    # アプリケーションスタイル
    app.setStyle("Fusion")

    # ダークテーマパレット
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

    # メインウィンドウ表示
    window = RehearsalWorkflowGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
