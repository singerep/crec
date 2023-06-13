import re
from collections import defaultdict
from typing import List

from crec.speaker import Speaker
from crec.text import Text
from crec.constants import TITLES

class Paragraph(Text):
    def __init__(self, granule_id: str, speaker: Speaker, speaking: bool, text: str) -> None:
        super().__init__(granule_id=granule_id, speaker=speaker, speaking=speaking, text=' '.join(text.split()))

    def __repr__(self) -> str:
        return f'\n---{self.speaker} (speaking: {self.speaking})---\n{self.text}'