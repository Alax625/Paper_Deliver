from paper_model import Paper


DIRECTION_KEYWORDS = {
    "语音合成": ["text-to-speech", "speech synthesis", "tts", "voice cloning"],
    "音乐生成": ["music generation", "music synthesis", "symbolic music", "singing voice"],
    "音频生成": ["audio generation", "audio synthesis", "text-to-audio", "sound generation"],
    "语音识别": ["speech recognition", "automatic speech recognition", "asr"],
    "语音翻译": ["speech translation", "speech-to-text translation", "spoken language translation"],
    "语音增强": ["speech enhancement", "speech separation", "noise suppression", "dereverberation"],
    "说话人": ["speaker recognition", "speaker verification", "speaker diarization", "speaker embedding"],
    "自监督学习": ["self-supervised", "self supervised", "ssl", "representation learning"],
}


def classify_paper(paper: Paper) -> str:
    text = f"{paper.title} {paper.summary}".casefold()
    best_direction = "其他"
    best_score = 0

    for direction, keywords in DIRECTION_KEYWORDS.items():
        score = sum(text.count(keyword) for keyword in keywords)
        if score > best_score:
            best_direction = direction
            best_score = score

    return best_direction
