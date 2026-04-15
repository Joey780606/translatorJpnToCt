# 翻譯模組：使用 Claude API (claude-haiku-4-5) 將日文翻譯為繁體中文
# 相較於 Google Translate，Claude 能理解語境、口語語氣與文化背景，翻譯更自然流暢

import json
import os
import time


class Translator:
    """使用 Claude API 進行日文→繁體中文字幕翻譯"""

    # 每批最多送出的段落數（避免單次請求 token 過多）
    _BatchSize = 20

    # 翻譯系統提示（固定不變，可被 prompt cache 命中，降低重複費用）
    _SystemPrompt = (
        "你是專業的日文字幕翻譯師，任務是將日文翻譯成自然流暢的繁體中文字幕。\n\n"
        "翻譯原則：\n"
        "1. 準確傳達原文語意，不遺漏、不添加\n"
        "2. 使用自然的繁體中文口語，避免逐字直譯造成的生硬感\n"
        "3. 保留說話者的語氣與情感（疑問、驚訝、憤怒、溫柔等）\n"
        "4. 人名、地名使用常見繁體中文譯法\n"
        "5. 字幕應簡潔，一般不超過 25 個繁體中文字\n\n"
        "輸出格式：\n"
        "- 輸入是 JSON 陣列，每個元素是一段日文字幕\n"
        "- 輸出必須是相同長度的 JSON 陣列，每個元素是對應的繁體中文翻譯\n"
        "- 只輸出 JSON，不要任何說明文字或 markdown 格式"
    )

    def __init__(self, ApiKey: str = ""):
        self._Client = None
        # 優先使用傳入的金鑰，其次讀取環境變數
        self._ApiKey = ApiKey.strip() if ApiKey else os.environ.get("ANTHROPIC_API_KEY", "")

    def SetApiKey(self, ApiKey: str):
        """更新 API 金鑰（重新設定時清除舊客戶端，下次呼叫自動重建）"""
        self._ApiKey = ApiKey.strip()
        self._Client = None

    def _HasApiKey(self) -> bool:
        """檢查是否已設定 API 金鑰"""
        return bool(self._ApiKey)

    def _LoadClient(self):
        """初始化 Anthropic 客戶端（延遲載入）"""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "找不到 anthropic 套件，請執行：\n"
                "pip install anthropic"
            )
        try:
            self._Client = anthropic.Anthropic(api_key=self._ApiKey)
        except Exception as E:
            raise RuntimeError(f"初始化 Claude 客戶端失敗：\n{E}")

    def _LoadGoogleTranslator(self):
        """初始化 Google 翻譯器（無 API 金鑰時的退回方案）"""
        try:
            from deep_translator import GoogleTranslator
            self._GoogleTranslator = GoogleTranslator(source="ja", target="zh-TW")
        except ImportError:
            raise RuntimeError(
                "找不到 deep-translator 套件，請執行：\n"
                "pip install deep-translator"
            )
        except Exception as E:
            raise RuntimeError(f"初始化 Google 翻譯器失敗：\n{E}")

    def _TranslateWithGoogle(self, JaText: str) -> str:
        """使用 Google Translate 翻譯單一段落（退回方案）"""
        if not hasattr(self, "_GoogleTranslator") or self._GoogleTranslator is None:
            self._LoadGoogleTranslator()
        for Attempt in range(3):
            try:
                Result = self._GoogleTranslator.translate(JaText.strip())
                return Result if Result else JaText
            except Exception:
                if Attempt < 2:
                    time.sleep(2 ** Attempt)
        return f"[翻譯失敗: {JaText}]"

    def _CallClaude(self, Texts: list) -> list:
        """
        呼叫 Claude API 翻譯一批日文段落，回傳繁體中文列表。
        系統提示使用 prompt caching，批次重複呼叫成本大幅降低。
        """
        Payload = json.dumps(Texts, ensure_ascii=False)
        UserMsg = f"請翻譯以下 JSON 陣列中的每一段日文為繁體中文：\n{Payload}"

        Response = self._Client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=[{
                "type": "text",
                "text": self._SystemPrompt,
                "cache_control": {"type": "ephemeral"}  # 系統提示 prompt caching
            }],
            messages=[{"role": "user", "content": UserMsg}]
        )

        RawText = Response.content[0].text.strip()

        # 移除可能的 markdown code block 包裝
        if RawText.startswith("```"):
            Lines = RawText.split("\n")
            RawText = "\n".join(Lines[1:-1]).strip()

        Translated = json.loads(RawText)

        if isinstance(Translated, list) and len(Translated) == len(Texts):
            return Translated

        # 長度不符時回傳原文，保留時間軸完整性
        return list(Texts)

    def Translate(self, JaText: str) -> str:
        """
        翻譯單一段落（供外部直接呼叫的介面）。
        有 API 金鑰：使用 Claude；無金鑰：自動退回 Google Translate。
        """
        if not JaText or not JaText.strip():
            return ""

        # 無 API 金鑰時，退回 Google Translate
        if not self._HasApiKey():
            return self._TranslateWithGoogle(JaText)

        if self._Client is None:
            self._LoadClient()

        try:
            Results = self._CallClaude([JaText.strip()])
            return Results[0] if Results else JaText
        except Exception:
            return f"[翻譯失敗: {JaText}]"

    def TranslateBatch(self, Texts: list, ProgressCallback=None) -> list:
        """
        批次翻譯日文段落列表，回傳對應長度的繁體中文列表。
        ProgressCallback(DoneCount, TotalCount): 進度回調（可選）
        有 API 金鑰：批次送給 Claude；無金鑰：退回 Google Translate 逐段翻譯。
        """
        if not Texts:
            return []

        Total = len(Texts)
        Results = list(Texts)  # 預設填入原文，逐批覆寫為翻譯結果

        # ── 無 API 金鑰：退回 Google Translate ────────────────────
        if not self._HasApiKey():
            for i, Text in enumerate(Texts):
                if Text and Text.strip():
                    Results[i] = self._TranslateWithGoogle(Text)
                if ProgressCallback:
                    ProgressCallback(i + 1, Total)
                if i < Total - 1:
                    time.sleep(0.3)  # 避免 Google 限流
            return Results

        # ── 有 API 金鑰：使用 Claude 批次翻譯 ────────────────────
        if self._Client is None:
            self._LoadClient()

        for BatchStart in range(0, Total, self._BatchSize):
            BatchEnd = min(BatchStart + self._BatchSize, Total)

            # 只取本批中非空的段落，保留原始索引
            BatchPairs = [
                (i, Texts[i].strip())
                for i in range(BatchStart, BatchEnd)
                if Texts[i] and Texts[i].strip()
            ]

            if not BatchPairs:
                if ProgressCallback:
                    ProgressCallback(BatchEnd, Total)
                continue

            BatchIndices = [p[0] for p in BatchPairs]
            BatchTexts = [p[1] for p in BatchPairs]

            # 嘗試批次翻譯（最多 3 次，指數退避）
            BatchOk = False
            for Attempt in range(3):
                try:
                    Translated = self._CallClaude(BatchTexts)
                    for Idx, Trans in zip(BatchIndices, Translated):
                        Results[Idx] = Trans if Trans else Texts[Idx]
                    BatchOk = True
                    break
                except json.JSONDecodeError:
                    if Attempt < 2:
                        time.sleep(1)
                except Exception:
                    if Attempt < 2:
                        time.sleep(2 ** Attempt)

            # 批次全部失敗時，降級為逐段翻譯
            if not BatchOk:
                for Idx, Text in zip(BatchIndices, BatchTexts):
                    Results[Idx] = self.Translate(Text)

            if ProgressCallback:
                ProgressCallback(BatchEnd, Total)

            if BatchEnd < Total:
                time.sleep(0.2)

        return Results
