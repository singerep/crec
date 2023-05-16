from xml.etree import ElementTree as et
from collections import defaultdict
import re
import requests

from crec import GovInfoAPI

# TODO: add ability to split text by speaker so that each speaker has 
# at most 1 document, or so that each speaker has 1 document per individual 
# time they speak

# TODO: put this in a constants file
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

class Granule(GovInfoAPI):
    def __init__(self, granule_id, api_key=None) -> None:
        super().__init__(api_key)

        self.granule_id = granule_id
        self.date = self.granule_id[5:15]

        self.parsed_name_map = {}
        self.raw_text = ''
        self.documents = defaultdict(str)

    def get(self):
        mods_url = self.base_url + f'packages/CREC-{self.date}/granules/{self.granule_id}/mods?api_key={self.api_key}'
        mods_content = requests.get(mods_url).content
        root = et.fromstring(mods_content)
        self.parse_xml(root)
        
        htm_url = self.base_url + f'packages/CREC-{self.date}/granules/{self.granule_id}/htm?api_key={self.api_key}'
        raw_text = requests.get(htm_url).text
        self.parse_htm(raw_text)


    def parse_xml(self, root: et):
        extension = root.find('{http://www.loc.gov/mods/v3}extension')
        members = extension.findall('{http://www.loc.gov/mods/v3}congMember')

        for member in members:
            bioguide_id = member.attrib['bioGuideId']
            names = member.findall('{http://www.loc.gov/mods/v3}name')
            parsed_name = [n for n in names if n.attrib['type'] == 'parsed'][0].text
            self.parsed_name_map[parsed_name] = bioguide_id

    def parse_htm(self, raw_text):
        self.raw_text = raw_text
        text = raw_text

        # remove heading
        heading_match = re.search('www\.gpo\.gov<\/a>\](\n)+', text)
        if heading_match is not None:
            text = text[heading_match.end():]

        # remove footer
        footer_match = re.search('(\n| )+____________________\n+', text)
        if footer_match is not None:
            text = text[:footer_match.start()]

        # remove page numbers
        text = re.sub('\s+\[\[Page .+\]\]\s+', '\n  ', text)

        # remove times
        text = re.sub('\s+\{time\}\s+\d+\s+', '\n  ', text)

        # remove notes
        # text = re.sub('=+ NOTE =+(?s).+=+ END NOTE =+', '\n', text)

        if len(self.parsed_name_map) == 1:
            current_speaker = list(self.parsed_name_map.keys())[0]
        else:
            current_speaker = None

        new_paragraph_matches = list(re.finditer('\n  ', text))
        for new_paragraph_id, new_paragraph_match in enumerate(new_paragraph_matches):
            paragraph_start = new_paragraph_match.end()
            paragraph_end = new_paragraph_matches[new_paragraph_id + 1].start() if new_paragraph_id < len(new_paragraph_matches) - 1 else -1
            paragraph_text = text[paragraph_start:paragraph_end]

            clipped_paragraph_text = paragraph_text

            good_paragraph = False
            if len(paragraph_text) == 0 or paragraph_text[0] == ' ' or paragraph_text[0] == '(':
                pass
            else:
                potential_first_sentence_split = re.split('(?<!Mr|Ms|Dr)\. ', paragraph_text, maxsplit=1)
                potential_first_sentence = potential_first_sentence_split[0]
                if any(re.search(t, potential_first_sentence) for t in TITLES):
                    current_speaker = None # TODO: should switch this so that it actually keeps track -- may not want to remove
                    if len(potential_first_sentence_split) == 1:
                        clipped_paragraph_text = ''
                    else:
                        clipped_paragraph_text = potential_first_sentence_split[1]
                else:
                    for parsed_name in self.parsed_name_map:
                        if paragraph_text[:len(parsed_name)] == parsed_name:
                            current_speaker = parsed_name
                            clipped_paragraph_text = paragraph_text[len(parsed_name) + 2:]

                good_paragraph = True

            if good_paragraph:
                if current_speaker:
                    current_speaker_id = self.parsed_name_map[current_speaker]
                    self.documents[current_speaker_id] += clipped_paragraph_text