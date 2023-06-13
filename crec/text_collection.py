from typing import List, Union
import pandas as pd

from crec.text import Text
from crec.speaker import UNKNOWN_SPEAKER

class TextCollection:
    def __init__(self, texts: List[Text] = None) -> None:
        self.texts = texts if texts is not None else []

    def __repr__(self) -> str:
        return '\n\n'.join(str(text) for text in self.texts)

    def add(self, text: Text):
        self.texts.append(text)

    def merge(self, other: 'TextCollection'):
        self.texts += other.texts

    def to_list(self):
        return self.texts

    def to_df(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, speaker_attributes: List[str] = ['bioGuideId']):
        text_dicts = []
        valid_text = [text for text in self.texts if (text.speaker != UNKNOWN_SPEAKER or include_unknown_speakers) and (text.speaking is True or include_non_speaking)]
        for text in valid_text:
            text_dict = {
                'granule_id': text.granule_id,
                'text': text.text,
                'speaker': text.speaker.first_last,
                'speaking': text.speaking
            }
            for attr in speaker_attributes:
                text_dict[attr] = text.speaker.get_attribute(attr)
            text_dicts.append(text_dict)

        return pd.DataFrame(text_dicts)