import re
from collections import defaultdict
from typing import List

from crec.speaker import Speaker
from crec.constants import TITLES

class Paragraph:
    def __init__(self, granule_id: str, previous_speaker: Speaker, speakers: List[Speaker], text: str) -> None:
        self.granule_id = granule_id
        self.speaker = None
        self.speaking = True

        for s in speakers:
            if text[:len(s.parsed_name)] == s.parsed_name:
                self.speaker = s
                text = text[len(s.parsed_name) + 2:]
                break

        self.text = ' '.join(text.split())

        if self.speaker is None:
            self.speaker = previous_speaker

        if len(text) == 0 or text[0] == ' ' or text[0] == '(':
            self.speaking = False

    def __repr__(self) -> str:
        return f'\n---{self.speaker}---\n{self.text}'


class ParagraphCollection:
    def __init__(self, granule_id: str) -> None:
        self.granule_id = granule_id
        self.speakers : List[Speaker] = []
        self.paragraphs : List[Paragraph] = []