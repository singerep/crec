import re
from typing import List

from crec.speaker import Speaker
from crec.paragraph import Paragraph
from crec.text import Text
from crec.text_collection import TextCollection

class Passage(Text):
    def __init__(self, granule_id: str, speaker: Speaker, speaking: bool = True, text: str = '') -> None:
        super().__init__(granule_id=granule_id, speaker=speaker, speaking=speaking, text=f'\n  {text}')

        self.paragraphs = TextCollection()
        self.split_into_paragraphs()

        self.text = self.text.strip()

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