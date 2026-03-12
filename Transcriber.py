# 語音辨識模組：使用 faster-whisper 將日文音訊轉換為文字段落


class Transcriber:
    """使用 faster-whisper small 模型進行日文語音辨識"""

    def __init__(self, ModelSize: str = "small"):
        self._Model = None
        self._ModelSize = ModelSize

    def _LoadModel(self):
        """載入 Whisper 模型（延遲載入，首次使用時才下載）"""
        try:
            from faster_whisper import WhisperModel
            self._Model = WhisperModel(
                self._ModelSize,
                device="cpu",
                compute_type="auto"    # 自動選擇最佳量化格式（int8 或 float32）
            )
        except ImportError:
            raise RuntimeError(
                "找不到 faster-whisper 套件，請執行:\n"
                "pip install faster-whisper"
            )
        except Exception as E:
            raise RuntimeError(f"載入 Whisper 模型失敗:\n{E}")

    def Transcribe(self, WavPath: str, ProgressCallback=None, StopCheck=None) -> list:
        """
        辨識 WAV 檔案中的日文語音，回傳段落列表
        ProgressCallback(CurrentTime, TotalDuration): 進度回調
        StopCheck(): 回傳 True 表示應停止
        """
        if self._Model is None:
            self._LoadModel()

        try:
            # 取得音訊時長用於進度計算
            import wave
            TotalDuration = 0.0
            try:
                with wave.open(WavPath, 'r') as WavFile:
                    TotalDuration = WavFile.getnframes() / WavFile.getframerate()
            except Exception:
                pass  # 無法取得時長時跳過進度計算

            # 執行語音辨識
            RawSegments, Info = self._Model.transcribe(
                WavPath,
                language="ja",          # 強制日文，避免誤判語言
                beam_size=5,
                vad_filter=True,        # 靜音偵測過濾，減少幻覺輸出
                vad_parameters={"min_silence_duration_ms": 500}
            )

            # 使用 Info 中的時長（較準確）
            if Info.duration and Info.duration > 0:
                TotalDuration = Info.duration

            Result = []
            Idx = 0

            # 逐段迭代 generator（實際辨識在此發生）
            for RawSeg in RawSegments:
                # 檢查是否要求停止
                if StopCheck and StopCheck():
                    break

                Idx += 1
                Result.append({
                    "Index": Idx,
                    "Start": RawSeg.start,
                    "End": RawSeg.end,
                    "JaText": RawSeg.text.strip()
                })

                # 回報進度
                if ProgressCallback and TotalDuration > 0:
                    ProgressCallback(RawSeg.end, TotalDuration)

            return Result

        except Exception as E:
            raise RuntimeError(f"語音辨識失敗:\n{E}")
