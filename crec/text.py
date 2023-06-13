from crec.speaker import Speaker

class Text:
    def __init__(self, granule_id: str, speaker: Speaker, speaking: bool, text: str) -> None:
        self.granule_id = granule_id
        self.speaker = speaker
        self.speaking = speaking
        self.text = text

    def __repr__(self) -> str:
        return f'---{self.speaker}---\n{self.text}'