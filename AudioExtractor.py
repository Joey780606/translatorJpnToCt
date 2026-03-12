# 音訊擷取模組：從影片檔擷取音訊並輸出為 Whisper 所需的 WAV 格式

import subprocess
import tempfile
import os


class AudioExtractor:
    """使用 ffmpeg 從影片中擷取音訊"""

    @staticmethod
    def Extract(VideoPath: str) -> str:
        """
        從影片擷取音訊，輸出 16kHz mono PCM WAV（Whisper 原生格式）
        回傳暫存 WAV 檔案路徑
        """
        # 建立暫存 WAV 檔案路徑
        TempDir = tempfile.gettempdir()
        TempWavPath = os.path.join(TempDir, "translatorJpnToCt_audio.wav")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", VideoPath,
                    "-vn",                    # 不輸出視訊
                    "-acodec", "pcm_s16le",   # 16-bit PCM
                    "-ar", "16000",           # 16kHz 取樣率
                    "-ac", "1",              # 單聲道
                    TempWavPath
                ],
                capture_output=True,
                check=True,
                timeout=600               # 最長等待 10 分鐘
            )
        except subprocess.CalledProcessError as E:
            # 解碼 ffmpeg 錯誤訊息
            ErrMsg = E.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"音訊擷取失敗:\n{ErrMsg}")
        except FileNotFoundError:
            raise RuntimeError(
                "找不到 ffmpeg，請先安裝 ffmpeg 並加入系統 PATH。\n"
                "下載網址: https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("音訊擷取逾時，請確認影片檔案是否正常。")

        return TempWavPath

    @staticmethod
    def GetDuration(VideoPath: str) -> float:
        """
        使用 ffprobe 取得影片時長（秒）
        失敗時回傳 0.0
        """
        try:
            Result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    VideoPath
                ],
                capture_output=True,
                check=True,
                timeout=30
            )
            return float(Result.stdout.decode().strip())
        except Exception:
            return 0.0
