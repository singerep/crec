from typing import List, Union
import re
import pandas as pd

from crec.speaker import Speaker, UNKNOWN_SPEAKER


class Paragraph:
    def __init__(self, granule_id: str, speaker: Speaker, speaking: bool, text: str) -> None:
        self.granule_id = granule_id
        self.speaker = speaker
        self.speaking = speaking
        self.text = ' '.join(text.split())

    def __repr__(self) -> str:
        return f'\n---{self} (speaking: {self.speaking})---\n{self.text}'


class Passage:
    def __init__(self, granule_id: str, speaker: Speaker, speaking: bool = True, text: str = '') -> None:
        self.granule_id = granule_id
        self.speaker = speaker
        self.speaking = speaking
        self.text = f'\n  {text}'

        self.paragraphs = TextCollection()
        self.split_into_paragraphs()

        self.text = ' '.join(self.text.split())

    def __repr__(self) -> str:
        return f'---{self.speaker}---\n' + self.clean_text

    def split_into_paragraphs(self):
        p_breaks = list(re.finditer(r'(?P<speaking>\n  (?! ))|(?P<nonspeaking>\n\n   +)', self.text))
        for i, match in enumerate(p_breaks):
            speaking = [k for k, v in match.groupdict().items() if v != None][0] == 'speaking'
            p_start = match.end()
            p_end = p_breaks[i + 1].start() if i < len(p_breaks) - 1 else None
            paragraph = Paragraph(granule_id=self.granule_id, speaker=self.speaker, speaking=speaking, text=self.text[p_start:p_end])
            self.paragraphs.add(paragraph)

    @property
    def clean_text(self):
        return '\n'.join([p.text for p in self.paragraphs.to_list()])


class TextCollection:
    def __init__(self, texts: List[Union[Paragraph, Passage]] = None) -> None:
        self.texts = texts if texts is not None else []

    def __repr__(self) -> str:
        return '\n\n'.join(str(text) for text in self.texts)

    def add(self, text: Union[Paragraph, Passage]):
        self.texts.append(text)

    def merge(self, other: 'TextCollection'):
        self.texts += other.texts

    def to_list(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, search: str = None) -> List[Union[Paragraph, Passage]]:
        valid_texts = []
        for text in self.texts:
            if include_unknown_speakers is False and text.speaker == UNKNOWN_SPEAKER:
                continue
            if include_non_speaking is False and text.speaking is False:
                continue
            if search is not None and search not in text.text.lower():
                continue

            valid_texts.append(text)

        return valid_texts

    def to_df(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, speaker_attributes: List[str] = ['bioGuideId'], search: str = None):
        text_dicts = []
        for text in self.to_list(include_unknown_speakers=include_unknown_speakers, include_non_speaking=include_non_speaking, search=search):
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


