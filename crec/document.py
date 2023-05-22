import re
from collections import defaultdict

TITLES = [
    'The PRESIDING OFFICER',
    'The SPEAKER',
    'The CHAIR',
    'The Acting CHAIR',
    'The ACTING PRESIDENT',
    'The PRESIDENT',
    'The CHIEF JUSTICE',
    'The VICE PRESIDENT',
    '(Mr\.|Ms\.|Miss) Counsel (?=\w*[A-Z]{2,})[A-Za-z]{3,}',
    '(Mr\.|Ms\.|Miss) Manager (?=\w*[A-Z]{2,})[A-Za-z]{3,}'
]

class Paragraph:
    def __init__(self, previous_speaker: str, parsed_name_map: dict, text: str) -> None:
        self.speaker = None
        self.speaker_id = None
        self.text = text
        self.valid = True

        potential_first_sentence_split = re.split('(?<!Mr|Ms|Dr)\. ', text, maxsplit=1)
        potential_first_sentence = potential_first_sentence_split[0]
        for t in TITLES:
            if re.search(t, potential_first_sentence):
                self.speaker = t
                text = potential_first_sentence_split[1] if len(potential_first_sentence_split) > 1 else ''
                break

        if self.speaker is None:
            for parsed_name in parsed_name_map:
                if text[:len(parsed_name)] == parsed_name:
                    self.speaker = parsed_name
                    self.speaker_id = parsed_name_map[parsed_name]
                    self.text = text[len(parsed_name) + 2:]
                    break

        if self.speaker is None:
            self.speaker = previous_speaker
            if previous_speaker in parsed_name_map:
                self.speaker_id = parsed_name_map[previous_speaker]

        if len(text) == 0 or text[0] == ' ' or text[0] == '(':
            self.valid = False


class Document:
    def __init__(self, key: str, speaker: str, speaker_id: str, text: str) -> None:
        self.key = key
        self.speaker = speaker
        self.speaker_id = speaker_id
        self.text = text

    def __repr__(self) -> str:
        return \
        f'''
        \n--- {self.speaker} ---
        {self.text}\n
        '''
    
    def add_paragraph(self, p: Paragraph):
        self.text += p.text.replace('\n', '')



class DocumentCollection:
    def __init__(self, group_by: str = 'speaker') -> None:
        self.group_by = group_by
        self.documents = {}

    def __repr__(self) -> str:
        return ''.join([str(d) for d_id, d in self.documents.items()])

    def add_paragraph(self, p: Paragraph, key_prefix: str = ''):
        if self.group_by == 'speaker':
            key = f'{key_prefix}{p.speaker_id}'
        else:
            raise NotImplementedError()
        
        if key in self.documents:
            self.documents[key].add_paragraph(p)
        else:
            d = Document(key, p.speaker, p.speaker_id, p.text)
            self.documents[key] = d

    def write(self, method: str = '*'):
        raise NotImplementedError()