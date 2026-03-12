# 翻譯模組：使用 deep_translator (Google Translate) 將日文翻譯為繁體中文

import time


class Translator:
    """使用 Google Translate 進行日文→繁體中文翻譯"""

    def __init__(self):
        self._Translator = None

    def _LoadTranslator(self):
        """初始化翻譯器（延遲載入）"""
        try:
            from deep_translator import GoogleTranslator
            self._Translator = GoogleTranslator(source="ja", target="zh-TW")
        except ImportError:
            raise RuntimeError(
                "找不到 deep-translator 套件，請執行:\n"
                "pip install deep-translator"
            )
        except Exception as E:
            raise RuntimeError(f"初始化翻譯器失敗:\n{E}")

    def Translate(self, JaText: str) -> str:
        """
        將日文文字翻譯為繁體中文
        翻譯失敗時回傳標記原文，不中斷整批翻譯流程
        """
        if not JaText or not JaText.strip():
            return ""

        if self._Translator is None:
            self._LoadTranslator()

        try:
            Result = self._Translator.translate(JaText.strip())
            return Result if Result else JaText
        except Exception:
            # 單段翻譯失敗時，等待一秒後重試一次
            try:
                time.sleep(1.0)
                Result = self._Translator.translate(JaText.strip())
                return Result if Result else JaText
            except Exception as E:
                # 重試仍失敗，標記原文並繼續
                return f"[翻譯失敗: {JaText}]"
