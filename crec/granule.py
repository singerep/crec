from xml.etree import ElementTree as et
from collections import defaultdict
import re
import httpx

from crec import GovInfoAPI
from crec.document import Paragraph, Document, DocumentCollection

# TODO: add ability to split text by speaker so that each speaker has 
# at most 1 document, or so that each speaker has 1 document per individual 
# time they speak

class Granule(GovInfoAPI):
    def __init__(self, granule_id, group_by: str = 'speaker', api_key=None) -> None:
        super().__init__(api_key)

        self.granule_id = granule_id
        self.date = self.granule_id[5:15]
        self.mods_url = self.base_url + f'packages/CREC-{self.date}/granules/{self.granule_id}/mods?api_key={self.api_key}'
        self.htm_url = self.base_url + f'packages/CREC-{self.date}/granules/{self.granule_id}/htm?api_key={self.api_key}'

        self.parsed_name_map = {}
        self.raw_text = ''
        self.paragraphs = []
        self.document_collection = DocumentCollection(group_by=group_by)

    def get(self, client = None):
        if isinstance(client, httpx.AsyncClient):
            self.async_get(client=client)
        else:
            mods_response = httpx.get(self.mods_url)
            htm_response = httpx.get(self.htm_url)

            self.parse_responses(mods_response, htm_response)

    async def async_get(self, client: httpx.AsyncClient):
        mods_response = await client.get(self.mods_url)
        htm_response = await client.get(self.htm_url)

        self.parse_responses(mods_response, htm_response)

    def parse_responses(self, mods_response, htm_response):
        mods_content = mods_response.content
        root = et.fromstring(mods_content)
        self.parse_xml(root)

        raw_text = htm_response.text
        self.parse_htm(raw_text)

    def parse_xml(self, root: et):
        for member in root.iter('{http://www.loc.gov/mods/v3}congMember'):
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

        paragraph_matches = list(re.finditer('\n  ', text))
        for paragraph_id, paragraph_match in enumerate(paragraph_matches):
            paragraph_start = paragraph_match.end()
            paragraph_end = paragraph_matches[paragraph_id + 1].start() if paragraph_id < len(paragraph_matches) - 1 else -1
            paragraph_text = text[paragraph_start:paragraph_end]

            p = Paragraph(current_speaker, self.parsed_name_map, paragraph_text)
            current_speaker = p.speaker

            if p.valid:
                self.documents.add_paragraph(p=p, key_prefix=f'{self.granule_id}_')

# SPENCER: blah blah blah
# ETHAN: sfoiansdof
# SPENCER: sadfoindso

# -> SPENCER: [blah blah blah sadfoindso], E

# group_by: speaker
#   each speaker in a granule has at most 1 document
# group_by: ______
#   each speaker in a granule has 1 document per each time they begin speaker