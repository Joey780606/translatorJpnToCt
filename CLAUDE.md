# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

使用者輸入本機內的影片存放位置後,
將影片裡的日文對話,以.srt的規格,
轉換成中文字幕檔(.srt),
並以"相同檔名.srt",將中文翻譯存於與影片相同的目錄.
希望此程式不需使用一般等級的NB也可以使用,不需要使用中,高級的顯示卡.

## Code Specification
1. 開發語言: Python 3.13
2. UI library: PySide6
3. 註解請用中文
4. Variable Naming: CamelCase is used consistently
5. Error Handling: All API calls must include a try-catch block

## UI Design（4 rows）

**Row 0 — 檔案選取及顯示列**
- `PBtnFile` (PushButton) : 顯示 "請選擇檔案名",按下後跳出檔案選擇的dialog,讓使用者選檔.選好後檔案路徑名稱顯示在下方的 LEPath 裡
- `LEPath`（QLineEdit）: 供操作者輸入檔案路徑名稱

**Row 1 — 翻譯與存檔列**
- `PBtnTranslation`（PushButton）: 顯示 "進行翻譯",按下後,開始做將日文發音轉成中文字幕處理,此時改成顯示"停止翻譯",再按下後,就中止翻譯。
- `PBtnSave`（PushButton）: 文字為 "存檔"。按下後以"相同檔名.srt"存於與影片相同的目錄。不管錯誤或失敗都跳出dialog顯示結果,錯誤的話多顯示失敗的原因。

**Row 2 — 進度條**
- `QPBar`（QProgressBar）: 顯示處理的進度(0~100)。

**Row 3 — 進度資料**
- `LblProgress`（Label）: 顯示處理狀態的文字,請依實際進度編寫文字。

**Row 4 — 翻譯資料顯示區**
- `TEdit`（TextEdit）: 顯示翻譯資料。

