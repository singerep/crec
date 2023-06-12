from xml.etree import ElementTree as et
from collections import defaultdict
import re
import httpx
from typing import List
import asyncio

from crec import GovInfoAPI
from crec.paragraph import Paragraph, ParagraphCollection
from crec.speaker import Speaker, UNKNOWN_SPEAKER
from crec.constants import TITLES


class Granule:
    def __init__(self, granule_id: str) -> None:
        self.granule_id = granule_id
        self.date = self.granule_id[5:15]
        self.mods_url = f'packages/CREC-{self.date}/granules/{self.granule_id}/mods'
        self.htm_url = f'packages/CREC-{self.date}/granules/{self.granule_id}/htm'

        self.raw_text = ''
        self.clean_text = ''
        self.paragraphs_collection = ParagraphCollection(granule_id=granule_id)

        self.valid = False

    def __repr__(self) -> str:
        return f'{self.granule_id}'

    def get(self, client = None):
        if isinstance(client, GovInfoAPI):
            self.async_get(client=client)
        else:
            mods_response = httpx.get(self.mods_url)
            htm_response = httpx.get(self.htm_url)

            self.parse_responses(mods_response, htm_response)

    async def async_get(self, client: GovInfoAPI):
        mods_response_validity, mods_response = await client.get(self.mods_url)
        htm_response_validity, htm_response = await client.get(self.htm_url)

        if mods_response_validity and htm_response_validity:
            self.parse_responses(mods_response, htm_response)
        else:
            pass

    def parse_responses(self, mods_response: httpx.Response, htm_response: httpx.Response):
        mods_content = mods_response.content
        root = et.fromstring(mods_content)
        self.parse_xml(root)

        raw_text = htm_response.text
        self.parse_htm(raw_text)

        self.valid = True

    def parse_xml(self, root: et):
        for member in root.iter('{http://www.loc.gov/mods/v3}congMember'):
            s = Speaker.from_member(member=member)
            self.paragraphs_collection.speakers.append(s)

    def parse_htm(self, raw_text):
        self.raw_text = raw_text
        text = raw_text

        # remove bullets
        text = re.sub('<bullet>', ' ', text)

        # remove title block
        title_block_match = re.search('\n\s+\b[A-Z][a-zA-Z]+\b(?:.*?\r?\n)+(?=\r?\n)', text)
        if title_block_match is not None:
            text = text[title_block_match.end():]

        # remove footer
        footer_match = re.search('(\n| )+____________________\n+', text)
        if footer_match is not None:
            text = text[:footer_match.start()]

        # remove bottom html
        bottom_html_match = re.search('\n+<\/pre><\/body>\n<\/html>', text)
        if bottom_html_match is not None:
            text = text[:bottom_html_match.start() + 1]

        # remove page numbers
        text = re.sub('\s+\[\[Page .+\](\s+|)', ' ', text)

        # remove times
        text = re.sub('\s+\{time\}\s+\d+(\s+|)', ' ', text)

        # remove notes
        # text = re.sub('=+ NOTE =+(?s).+=+ END NOTE =+', '\n', text)

        self.clean_text = text

        self.find_titled_speakers()
        self.find_paragraphs()

    def find_titled_speakers(self):
        titled_speakers = set()
        for t in TITLES:
            for match in re.findall(t, self.clean_text):
                if match not in titled_speakers:
                    titled_speakers.add(match)
                    s = Speaker.from_title(title=match)
                    self.paragraphs_collection.speakers.append(s)

        self.paragraphs_collection.speakers = sorted(self.paragraphs_collection.speakers, key=lambda s : len(s.parsed_name), reverse=True)

    def find_paragraphs(self):
        if len(self.paragraphs_collection.speakers) == 1:
            current_speaker = self.paragraphs_collection.speakers[0]
        else:
            current_speaker = UNKNOWN_SPEAKER

        paragraph_matches = list(re.finditer('\n  ', self.clean_text))
        for paragraph_id, paragraph_match in enumerate(paragraph_matches):
            paragraph_start = paragraph_match.end()
            paragraph_end = paragraph_matches[paragraph_id + 1].start() if paragraph_id < len(paragraph_matches) - 1 else -1
            paragraph_text = self.clean_text[paragraph_start:paragraph_end]

            p = Paragraph(granule_id=self.granule_id, previous_speaker=current_speaker, speakers=self.paragraphs_collection.speakers, text=paragraph_text)
            current_speaker = p.speaker
            self.paragraphs_collection.paragraphs.append(p)