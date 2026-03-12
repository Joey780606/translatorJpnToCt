# SRT 字幕格式組建模組


class SrtBuilder:
    """負責將字幕段落資料組建為 SRT 格式字串"""

    @staticmethod
    def FormatTimecode(Seconds: float) -> str:
        """將秒數轉換為 SRT 時間碼格式 HH:MM:SS,mmm"""
        Hours = int(Seconds // 3600)
        Minutes = int((Seconds % 3600) // 60)
        Secs = int(Seconds % 60)
        Millis = int(round((Seconds - int(Seconds)) * 1000))
        # 防止毫秒溢位
        if Millis >= 1000:
            Millis = 999
        return f"{Hours:02d}:{Minutes:02d}:{Secs:02d},{Millis:03d}"

    @staticmethod
    def FormatChunk(Segment: dict) -> str:
        """格式化單一字幕段落，用於即時顯示在 TEdit"""
        StartTc = SrtBuilder.FormatTimecode(Segment["Start"])
        EndTc = SrtBuilder.FormatTimecode(Segment["End"])
        ZhText = Segment.get("ZhText", Segment.get("JaText", ""))
        return f'{Segment["Index"]}\n{StartTc} --> {EndTc}\n{ZhText}\n'

    @staticmethod
    def Build(Segments: list) -> str:
        """組建完整的 SRT 字串"""
        Lines = []
        for Seg in Segments:
            Lines.append(SrtBuilder.FormatChunk(Seg))
            Lines.append("")  # 每段之間的空行
        return "\n".join(Lines)
