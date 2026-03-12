# 日文影片轉中文字幕翻譯器 — 實作計畫

## Context

使用者需要一個桌面應用程式，可以選取本機影片檔，
自動將日文語音辨識並翻譯為中文字幕（.srt），
儲存於與影片相同的目錄。
需可在普通筆電（無高階 GPU）上執行。

---

## 技術選型

| 項目 | 選擇 | 理由 |
|------|------|------|
| ASR 引擎 | faster-whisper (`small` model) | CPU + int8 量化，速度與精度最佳平衡 |
| 翻譯 | deep_translator (Google Translate) | 免費、免 API Key、日中品質最佳 |
| 音訊擷取 | subprocess + ffmpeg | 輕量、精確控制輸出格式 |
| 執行緒 | QThread subclass | 清楚邊界、可協作式停止 |
| SRT 編碼 | UTF-8 with BOM | Windows 媒體播放器相容 |

---

## 檔案結構

```
translatorJpnToCt/
├── main.py                  # 程式進入點
├── MainWindow.py            # 主視窗 UI
├── TranslationWorker.py     # QThread 工作執行緒（核心協調者）
├── AudioExtractor.py        # ffmpeg 音訊擷取
├── Transcriber.py           # faster-whisper 語音辨識
├── Translator.py            # deep_translator 日→中翻譯
├── SrtBuilder.py            # SRT 格式組建
└── requirements.txt
```

---

## 模組設計

### `main.py`
- 建立 `QApplication` 並啟動 `MainWindow`

### `MainWindow.py` — `MainWindow(QMainWindow)`

UI 元件（依 CLAUDE.md 規格）：
- **Row 0**: `PBtnFile`（"請選擇檔案名"） + `LEPath`（QLineEdit）
- **Row 1**: `PBtnTranslation`（切換"進行翻譯"/"停止翻譯"） + `PBtnSave`（"存檔"）
- **Row 2**: `QPBar`（QProgressBar 0–100）
- **Row 3**: `LblProgress`（QLabel 狀態文字）
- **Row 4**: `TEdit`（QTextEdit 顯示翻譯字幕）

關鍵 slots：
- `SlotSelectFile()` — QFileDialog 選片，寫入 LEPath
- `SlotToggleTranslation()` — 啟動/停止 `TranslationWorker`
- `SlotSaveFile()` — 儲存 `self._SrtContent` 為 .srt，用 QMessageBox 顯示結果
- `SlotProgressUpdated(Value, Message)` — 更新 QPBar + LblProgress
- `SlotSubtitleChunkReady(ChunkText)` — `TEdit.append()` 即時追加
- `SlotFinished(SrtContent)` — 儲存 `_SrtContent`，啟用存檔按鈕
- `SlotErrorOccurred(ErrorMessage)` — QMessageBox.critical
- `SlotStopped()` — 重設按鈕狀態

### `TranslationWorker.py` — `TranslationWorker(QThread)`

Signals:
```python
ProgressUpdated    = Signal(int, str)   # (百分比, 狀態文字)
SubtitleChunkReady = Signal(str)        # 每段完成
Finished           = Signal(str)        # 完成，帶 SRT 全文
ErrorOccurred      = Signal(str)
Stopped            = Signal()
```

`run()` 四個階段：
1. **音訊擷取** (0→10%) — `AudioExtractor.Extract()`
2. **語音辨識** (10→60%) — 迭代 faster-whisper generator，用 `RawSeg.end / Duration` 計算進度，同時檢查 `_StopRequested`
3. **翻譯** (60→95%) — 逐段 `Translator.Translate()`，每段後 `SubtitleChunkReady.emit()`，檢查 `_StopRequested`
4. **組建 SRT** (95→100%) — `SrtBuilder.Build()`，`Finished.emit()`

停止機制：`RequestStop()` 設 `self._StopRequested = True`（協作式取消，在迴圈間檢查）

### `AudioExtractor.py` — `AudioExtractor`
```python
AudioExtractor.Extract(VideoPath) → TempWavPath
# ffmpeg -i VideoPath -vn -acodec pcm_s16le -ar 16000 -ac 1 TempWavPath
# 16kHz mono PCM WAV = Whisper 原生格式
```

### `Transcriber.py` — `Transcriber`
```python
WhisperModel("small", device="cpu", compute_type="int8")
model.transcribe(WavPath, language="ja", vad_filter=True, beam_size=5)
# vad_filter 過濾靜音，減少幻覺輸出
```

### `Translator.py` — `Translator`
```python
GoogleTranslator(source="ja", target="zh-TW")
# 翻譯失敗時回傳 "[翻譯失敗: 原文]"，不中斷整個流程
```

### `SrtBuilder.py` — `SrtBuilder`
```python
FormatTimecode(Seconds: float) → "HH:MM:SS,mmm"
FormatChunk(Segment: dict) → str     # 單段字幕（即時顯示用）
Build(Segments: list[dict]) → str    # 完整 SRT 字串
```

---

## 進度計算

| 階段 | 範圍 | 計算方式 |
|------|------|----------|
| 音訊擷取 | 0→10 | 完成時跳到 10 |
| 語音辨識 | 10→60 | `10 + (RawSeg.end / Duration) * 50` |
| 翻譯 | 60→95 | `60 + (i / Total) * 35` |
| SRT 組建 | 95→100 | 完成時跳到 100 |

---

## requirements.txt

```
PySide6>=6.6.0
faster-whisper>=1.0.0
deep-translator>=1.11.4
```

系統相依：`ffmpeg`（需安裝並加入 PATH）

---

## 注意事項

1. **首次執行** — `faster-whisper` 會自動下載 `small` model (~244MB)，顯示 "正在下載 Whisper 模型..."
2. **ffmpeg 未安裝** — `AudioExtractor` 拋出 `RuntimeError`，顯示友善提示訊息
3. **翻譯失敗** — 單段失敗時標記原文繼續，不中斷整批翻譯
4. **停止後** — `_SrtContent` 不設定，`PBtnSave` 保持停用（避免儲存不完整字幕）
5. **SRT 編碼** — `utf-8-sig`（含 BOM）確保 Windows 媒體播放器正確顯示中文

---

## 驗證方式

1. 執行 `python main.py`，確認視窗正常顯示
2. 點擊"請選擇檔案名"，選取一個含日文對話的影片（如 .mp4）
3. 點擊"進行翻譯"，確認：
   - 按鈕切換為"停止翻譯"
   - QPBar 進度更新
   - LblProgress 狀態文字更新
   - TEdit 逐段顯示字幕
4. 翻譯完成後，確認"存檔"可用，點擊後 .srt 存於影片同目錄
5. 用媒體播放器（PotPlayer/VLC）載入影片與字幕，確認中文正常顯示
6. 測試中途點擊"停止翻譯"，確認流程正常中止
