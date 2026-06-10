# 翻譯工作執行緒：在背景執行音訊擷取、語音辨識、翻譯的完整流程

import os
import time
from PySide6.QtCore import QThread, Signal

from AudioExtractor import AudioExtractor
from Transcriber import Transcriber
from Translator import Translator
from SrtBuilder import SrtBuilder


class TranslationWorker(QThread):
    """背景執行緒，協調四個處理階段並透過 Signal 回報進度給主視窗"""

    # 進度更新 Signal (百分比 0-100, 狀態文字)
    ProgressUpdated = Signal(int, str)
    # 每段字幕翻譯完成 Signal (單段 SRT 文字)
    SubtitleChunkReady = Signal(str)
    # 全部完成 Signal (完整 SRT 字串)
    Finished = Signal(str)
    # 發生錯誤 Signal (錯誤訊息)
    ErrorOccurred = Signal(str)
    # 使用者停止 Signal
    Stopped = Signal()

    def __init__(self, VideoPath: str, ApiKey: str = ""):
        super().__init__()
        self._VideoPath = VideoPath
        self._ApiKey = ApiKey          # Anthropic API 金鑰
        self._StopRequested = False    # 協作式停止旗標

    def RequestStop(self):
        """要求停止翻譯（協作式取消，在迴圈間生效）"""
        self._StopRequested = True

    def run(self):
        """主執行緒入口，依序執行四個處理階段"""
        TempWavPath = None

        try:
            # ── 階段 1：音訊擷取 (0→10%) ─────────────────────────────
            self.ProgressUpdated.emit(0, "正在擷取音訊...")

            TempWavPath = AudioExtractor.Extract(self._VideoPath)

            if self._StopRequested:
                self._Cleanup(TempWavPath)
                self.Stopped.emit()
                return

            self.ProgressUpdated.emit(10, "音訊擷取完成，準備語音辨識...")

            # ── 階段 2：語音辨識 (10→60%) ────────────────────────────
            self.ProgressUpdated.emit(10, "正在載入 Whisper 模型（首次使用需下載）...")

            TranscriberInstance = Transcriber(ModelSize="small")

            def OnTranscribeProgress(CurrentTime, TotalDuration):
                """辨識進度回調，計算 10~60% 的進度"""
                if TotalDuration > 0:
                    Pct = 10 + int((CurrentTime / TotalDuration) * 50)
                    Pct = min(Pct, 59)   # 不超過階段上限
                    self.ProgressUpdated.emit(
                        Pct,
                        f"語音辨識中... {CurrentTime:.0f}s / {TotalDuration:.0f}s"
                    )

            Segments = TranscriberInstance.Transcribe(
                TempWavPath,
                ProgressCallback=OnTranscribeProgress,
                StopCheck=lambda: self._StopRequested
            )

            if self._StopRequested:
                self._Cleanup(TempWavPath)
                self.Stopped.emit()
                return

            if not Segments:
                self._Cleanup(TempWavPath)
                self.ErrorOccurred.emit("語音辨識未偵測到任何語音段落，請確認影片是否含有日文對話。")
                return

            self.ProgressUpdated.emit(60, f"語音辨識完成，共 {len(Segments)} 段，準備翻譯...")

            # ── 階段 3：翻譯 (60→95%) ────────────────────────────────
            TranslatorInstance = Translator(ApiKey=self._ApiKey)
            Total = len(Segments)
            BatchSize = Translator._BatchSize

            # 逐批翻譯並立即顯示，讓使用者可以即時看到字幕（不必等全部完成）
            for BatchStart in range(0, Total, BatchSize):
                if self._StopRequested:
                    self._Cleanup(TempWavPath)
                    self.Stopped.emit()
                    return

                BatchEnd = min(BatchStart + BatchSize, Total)
                BatchSegs = Segments[BatchStart:BatchEnd]
                JaBatch = [Seg["JaText"] for Seg in BatchSegs]

                # 翻譯這一批
                ZhBatch = TranslatorInstance.TranslateSingleBatch(JaBatch)

                # 即時發出這批字幕供 TEdit 顯示
                for i, Seg in enumerate(BatchSegs):
                    Seg["ZhText"] = ZhBatch[i] if i < len(ZhBatch) else Seg["JaText"]
                    ChunkText = SrtBuilder.FormatChunk(Seg)
                    self.SubtitleChunkReady.emit(ChunkText)

                # 更新進度
                Pct = 60 + int((BatchEnd / Total) * 35)
                self.ProgressUpdated.emit(
                    min(Pct, 94),
                    f"翻譯中 {BatchEnd} / {Total}..."
                )

                # 批次間稍作停頓（Claude 路徑）
                if BatchEnd < Total and self._ApiKey:
                    time.sleep(0.2)

            # ── 階段 4：組建 SRT (95→100%) ───────────────────────────
            self.ProgressUpdated.emit(95, "正在組建字幕檔...")
            SrtContent = SrtBuilder.Build(Segments)

            self._Cleanup(TempWavPath)
            self.ProgressUpdated.emit(100, "翻譯完成！")
            self.Finished.emit(SrtContent)

        except RuntimeError as E:
            self._Cleanup(TempWavPath)
            self.ErrorOccurred.emit(str(E))
        except Exception as E:
            self._Cleanup(TempWavPath)
            self.ErrorOccurred.emit(f"發生未預期的錯誤:\n{E}")

    def _Cleanup(self, TempWavPath: str):
        """刪除暫存音訊檔案"""
        if TempWavPath and os.path.exists(TempWavPath):
            try:
                os.remove(TempWavPath)
            except Exception:
                pass  # 刪除失敗時靜默忽略
