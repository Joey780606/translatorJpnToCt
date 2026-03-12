# 主視窗 UI 模組

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QProgressBar, QLabel,
    QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from TranslationWorker import TranslationWorker


class MainWindow(QMainWindow):
    """主視窗，包含所有 UI 元件及翻譯流程控制"""

    def __init__(self):
        super().__init__()
        self._Worker = None          # 目前的翻譯工作執行緒
        self._SrtContent = ""        # 翻譯完成的 SRT 字串
        self._SetupUi()

    def _SetupUi(self):
        """建立並排列所有 UI 元件"""
        self.setWindowTitle("日文影片轉中文字幕")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        CentralWidget = QWidget()
        self.setCentralWidget(CentralWidget)
        MainLayout = QVBoxLayout(CentralWidget)
        MainLayout.setSpacing(8)
        MainLayout.setContentsMargins(12, 12, 12, 12)

        # ── Row 0：檔案選取列 ───────────────────────────────────────
        Row0Layout = QHBoxLayout()
        self.PBtnFile = QPushButton("請選擇檔案名")
        self.PBtnFile.setFixedWidth(120)
        self.LEPath = QLineEdit()
        self.LEPath.setPlaceholderText("影片檔案路徑")
        Row0Layout.addWidget(self.PBtnFile)
        Row0Layout.addWidget(self.LEPath)
        MainLayout.addLayout(Row0Layout)

        # ── Row 1：翻譯與存檔列 ────────────────────────────────────
        Row1Layout = QHBoxLayout()
        self.PBtnTranslation = QPushButton("進行翻譯")
        self.PBtnTranslation.setFixedWidth(100)
        self.PBtnSave = QPushButton("存檔")
        self.PBtnSave.setFixedWidth(80)
        self.PBtnSave.setEnabled(False)    # 翻譯完成後才啟用
        Row1Layout.addWidget(self.PBtnTranslation)
        Row1Layout.addWidget(self.PBtnSave)
        Row1Layout.addStretch()
        MainLayout.addLayout(Row1Layout)

        # ── Row 2：進度條 ──────────────────────────────────────────
        self.QPBar = QProgressBar()
        self.QPBar.setRange(0, 100)
        self.QPBar.setValue(0)
        self.QPBar.setTextVisible(True)
        MainLayout.addWidget(self.QPBar)

        # ── Row 3：進度文字 ────────────────────────────────────────
        self.LblProgress = QLabel("請選擇影片檔案")
        self.LblProgress.setAlignment(Qt.AlignmentFlag.AlignLeft)
        MainLayout.addWidget(self.LblProgress)

        # ── Row 4：翻譯資料顯示區 ──────────────────────────────────
        self.TEdit = QTextEdit()
        self.TEdit.setReadOnly(True)
        self.TEdit.setPlaceholderText("翻譯後的字幕將顯示於此...")
        MainLayout.addWidget(self.TEdit)

        # 連接 Signals
        self._ConnectSignals()

    def _ConnectSignals(self):
        """連接所有 UI 元件的 Signals"""
        self.PBtnFile.clicked.connect(self.SlotSelectFile)
        self.PBtnTranslation.clicked.connect(self.SlotToggleTranslation)
        self.PBtnSave.clicked.connect(self.SlotSaveFile)

    # ── Slots ──────────────────────────────────────────────────────

    def SlotSelectFile(self):
        """開啟檔案選擇對話框，讓使用者選取影片檔案"""
        FilePath, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片檔案",
            "",
            "影片檔案 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.ts *.m2ts);;所有檔案 (*)"
        )
        if FilePath:
            self.LEPath.setText(FilePath)
            self.LblProgress.setText("已選擇檔案，點擊「進行翻譯」開始處理")
            self._SrtContent = ""
            self.PBtnSave.setEnabled(False)
            self.TEdit.clear()
            self.QPBar.setValue(0)

    def SlotToggleTranslation(self):
        """切換翻譯狀態：開始翻譯或停止翻譯"""
        if self.PBtnTranslation.text() == "進行翻譯":
            # 驗證檔案路徑
            VideoPath = self.LEPath.text().strip()
            if not VideoPath:
                QMessageBox.warning(self, "警告", "請先選擇影片檔案。")
                return
            if not os.path.isfile(VideoPath):
                QMessageBox.warning(self, "警告", f"找不到檔案:\n{VideoPath}")
                return

            # 清除前次結果
            self.TEdit.clear()
            self.QPBar.setValue(0)
            self._SrtContent = ""
            self.PBtnSave.setEnabled(False)

            # 建立並啟動工作執行緒
            self._Worker = TranslationWorker(VideoPath)
            self._Worker.ProgressUpdated.connect(self.SlotProgressUpdated)
            self._Worker.SubtitleChunkReady.connect(self.SlotSubtitleChunkReady)
            self._Worker.Finished.connect(self.SlotFinished)
            self._Worker.ErrorOccurred.connect(self.SlotErrorOccurred)
            self._Worker.Stopped.connect(self.SlotStopped)
            self._Worker.start()

            self.PBtnTranslation.setText("停止翻譯")
            self.PBtnFile.setEnabled(False)
            self.LEPath.setEnabled(False)

        else:
            # 要求停止翻譯
            if self._Worker and self._Worker.isRunning():
                self._Worker.RequestStop()
            self.PBtnTranslation.setEnabled(False)    # 防止重複點擊
            self.LblProgress.setText("正在停止翻譯，請稍候...")

    def SlotSaveFile(self):
        """將翻譯結果存為 .srt 檔案"""
        if not self._SrtContent:
            QMessageBox.warning(self, "警告", "目前沒有可儲存的字幕內容。")
            return

        VideoPath = self.LEPath.text().strip()
        BaseName = os.path.splitext(VideoPath)[0]
        SrtPath = BaseName + ".srt"

        try:
            # utf-8-sig 含 BOM，確保 Windows 媒體播放器正確顯示中文
            with open(SrtPath, "w", encoding="utf-8-sig") as F:
                F.write(self._SrtContent)
            QMessageBox.information(
                self, "存檔成功",
                f"字幕已成功儲存至:\n{SrtPath}"
            )
        except PermissionError as E:
            QMessageBox.critical(
                self, "存檔失敗",
                f"權限不足，無法寫入檔案:\n{SrtPath}\n\n{E}"
            )
        except OSError as E:
            QMessageBox.critical(
                self, "存檔失敗",
                f"檔案寫入失敗:\n{E}"
            )

    def SlotProgressUpdated(self, Value: int, Message: str):
        """更新進度條與狀態文字"""
        self.QPBar.setValue(Value)
        self.LblProgress.setText(Message)

    def SlotSubtitleChunkReady(self, ChunkText: str):
        """即時追加顯示已翻譯的字幕段落"""
        self.TEdit.append(ChunkText)

    def SlotFinished(self, SrtContent: str):
        """翻譯全部完成的處理"""
        self._SrtContent = SrtContent
        self.PBtnTranslation.setText("進行翻譯")
        self.PBtnTranslation.setEnabled(True)
        self.PBtnFile.setEnabled(True)
        self.LEPath.setEnabled(True)
        self.PBtnSave.setEnabled(True)
        self.QPBar.setValue(100)
        self.LblProgress.setText("翻譯完成！點擊「存檔」儲存字幕檔。")

    def SlotErrorOccurred(self, ErrorMessage: str):
        """翻譯過程發生錯誤的處理"""
        self.PBtnTranslation.setText("進行翻譯")
        self.PBtnTranslation.setEnabled(True)
        self.PBtnFile.setEnabled(True)
        self.LEPath.setEnabled(True)
        self.LblProgress.setText("發生錯誤，翻譯中止。")
        QMessageBox.critical(self, "翻譯錯誤", ErrorMessage)

    def SlotStopped(self):
        """使用者主動停止翻譯的處理"""
        self.PBtnTranslation.setText("進行翻譯")
        self.PBtnTranslation.setEnabled(True)
        self.PBtnFile.setEnabled(True)
        self.LEPath.setEnabled(True)
        self.LblProgress.setText("已停止翻譯。")
