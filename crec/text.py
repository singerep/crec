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

        self.paragraph_collection = ParagraphCollection()
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
            self.paragraph_collection.add(paragraph)

    @property
    def clean_text(self):
        return '\n'.join([p.text for p in self.paragraph_collection.paragraphs])


class ParagraphCollection:
    def __init__(self) -> None:
        self.paragraphs : List[Paragraph] = []

    def merge(self, other: 'ParagraphCollection') -> None:
        self.paragraphs += other.paragraphs

    def add(self, paragraph: Paragraph):
        self.paragraphs.append(paragraph)

    def to_list(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, search: str = None) -> List[Paragraph]:
        valid_paragraphs = []
        for paragraph in self.paragraphs:
            if include_unknown_speakers is False and paragraph.speaker == UNKNOWN_SPEAKER:
                continue
            if include_non_speaking is False and paragraph.speaking is False:
                continue
            if search is not None and search.lower() not in paragraph.text.lower():
                continue

            valid_paragraphs.append(paragraph)

        return valid_paragraphs

    def to_df(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, speaker_attributes: List[str] = ['bioGuideId'], search: str = None) -> pd.DataFrame:
        valid_paragraphs = self.to_list(include_unknown_speakers=include_unknown_speakers, include_non_speaking=include_non_speaking, search=search)
        paragraph_dicts = []
        for paragraph in valid_paragraphs:
            paragraph_dict = {
                'granule_id': paragraph.granule_id,
                'text': paragraph.text,
                'speaker': paragraph.speaker.first_last,
                'speaking': paragraph.speaking
            }
            for attr in speaker_attributes:
                paragraph_dict[attr] = paragraph.speaker.get_attribute(attr)
            paragraph_dicts.append(paragraph_dict)

        return pd.DataFrame(paragraph_dicts)


class PassageCollection:
    def __init__(self) -> None:
        self.passages : List[Passage] = []

    def merge(self, other: 'PassageCollection') -> None:
        self.passages += other.passages

    def add(self, passage: Passage):
        self.passages.append(passage)

    def to_list(self, include_unknown_speakers: bool = False, search: str = None) -> List[Passage]:
        valid_passages = []
        for passage in self.passages:
            if include_unknown_speakers is False and passage.speaker == UNKNOWN_SPEAKER:
                continue
            if search is not None and search.lower() not in passage.text.lower():
                continue

            valid_passages.append(passage)

        return valid_passages

    def to_df(self, include_unknown_speakers: bool = False, speaker_attributes: List[str] = ['bioGuideId'], search: str = None) -> pd.DataFrame:
        valid_passages = self.to_list(include_unknown_speakers=include_unknown_speakers, search=search)
        passage_dicts = []
        for passage in valid_passages:
            passage_dict = {
                'granule_id': passage.granule_id,
                'text': passage.text,
                'speaker': passage.speaker.first_last
            }
            for attr in speaker_attributes:
                passage_dict[attr] = passage.speaker.get_attribute(attr)
            passage_dicts.append(passage_dict)

        return pd.DataFrame(passage_dicts)


class TextCollection:
    def __init__(self) -> None:
        self.paragraph_collection = ParagraphCollection()
        self.passage_collection = PassageCollection()

    def merge(self, other: 'TextCollection') -> None:
        self.paragraph_collection.merge(other=other.paragraph_collection)
        self.passage_collection.merge(other=other.passage_collection)

    def add_passage(self, passage: Passage) -> None:
        self.passage_collection.add(passage=passage)
        for paragraph in passage.paragraph_collection.paragraphs:
            self.paragraph_collection.add(paragraph=paragraph)
    
    def add_paragraph(self, paragraph: Paragraph) -> None:
        self.paragraph_collection.add(paragraph=paragraph)

    def to_list(self, unit: str = 'passage'):
        if unit == 'passage':
            return self.passage_collection.to_list()
        elif unit == 'paragraph':
            return self.paragraph_collection.to_list()
        else:
            raise ValueError("unit must be passage or paragraph")

    def to_df(self, unit: str = 'passage'):
        if unit == 'passage':
            return self.passage_collection.to_df()
        elif unit == 'paragraph':
            return self.paragraph_collection.to_df()
        else:
            raise ValueError("unit must be passage or paragraph")