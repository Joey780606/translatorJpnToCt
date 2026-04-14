# 翻譯模組：使用 deep_translator (Google Translate) 將日文翻譯為繁體中文

import time


class Translator:
    """使用 Google Translate 進行日文→繁體中文翻譯"""

    # 每批最多送出的段落數（避免單次請求字數過多）
    _BatchSize = 30

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

    def _ReinitTranslator(self):
        """重新初始化翻譯器（連線異常時使用）"""
        try:
            from deep_translator import GoogleTranslator
            self._Translator = GoogleTranslator(source="ja", target="zh-TW")
        except Exception:
            pass

    def _TranslateSingle(self, JaText: str) -> str:
        """
        翻譯單一段落，含指數退避重試（最多3次）
        失敗時回傳原文並加標記
        """
        for Attempt in range(3):
            try:
                Result = self._Translator.translate(JaText.strip())
                return Result if Result else JaText
            except Exception:
                if Attempt < 2:
                    # 指數退避：1s、2s
                    time.sleep(2 ** Attempt)
                    self._ReinitTranslator()
                else:
                    return f"[翻譯失敗: {JaText}]"
        return f"[翻譯失敗: {JaText}]"

    def Translate(self, JaText: str) -> str:
        """
        將日文文字翻譯為繁體中文（單段介面，供外部直接呼叫）
        翻譯失敗時回傳標記原文，不中斷整批翻譯流程
        """
        if not JaText or not JaText.strip():
            return ""

        if self._Translator is None:
            self._LoadTranslator()

        return self._TranslateSingle(JaText)

    def TranslateBatch(self, Texts: list, ProgressCallback=None) -> list:
        """
        批次翻譯日文段落列表，回傳對應長度的中文列表。
        ProgressCallback(DoneCount, TotalCount): 進度回調（可選）
        每批失敗時自動降級為逐段翻譯，確保最大覆蓋率。
        """
        if not Texts:
            return []

        if self._Translator is None:
            self._LoadTranslator()

        Total = len(Texts)
        Results = [""] * Total

        # 分批處理，每批 _BatchSize 段
        for BatchStart in range(0, Total, self._BatchSize):
            BatchEnd = min(BatchStart + self._BatchSize, Total)
            # 只取本批中非空的段落
            BatchPairs = [
                (i, Texts[i].strip())
                for i in range(BatchStart, BatchEnd)
                if Texts[i] and Texts[i].strip()
            ]

            if not BatchPairs:
                continue

            BatchIndices = [p[0] for p in BatchPairs]
            BatchTexts = [p[1] for p in BatchPairs]

            # 嘗試批次翻譯（最多3次，指數退避）
            BatchSuccess = False
            for Attempt in range(3):
                try:
                    Translated = self._Translator.translate_batch(BatchTexts)
                    for Idx, Trans in zip(BatchIndices, Translated):
                        Results[Idx] = Trans if Trans else Texts[Idx]
                    BatchSuccess = True
                    break
                except Exception:
                    if Attempt < 2:
                        time.sleep(2 ** Attempt)
                        self._ReinitTranslator()

            # 批次失敗時，降級為逐段翻譯
            if not BatchSuccess:
                for Idx, Text in zip(BatchIndices, BatchTexts):
                    Results[Idx] = self._TranslateSingle(Text)

            # 回報進度
            if ProgressCallback:
                ProgressCallback(BatchEnd, Total)

            # 批次之間稍作停頓，降低被限流的機率
            if BatchEnd < Total:
                time.sleep(0.5)

        return Results
