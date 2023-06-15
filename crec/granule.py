from xml.etree import ElementTree as et
from collections import defaultdict, namedtuple
import re
import httpx
from typing import List, Dict
import asyncio
from itertools import chain

from crec import GovInfoClient
from crec.speaker import Speaker, UNKNOWN_SPEAKER
from crec.constants import TITLES
from crec.text import Passage, TextCollection


class Granule:
    def __init__(self, granule_id: str) -> None:
        self.granule_id = granule_id
        self.date = self.granule_id[5:15]
        self.mods_url = f'packages/CREC-{self.date}/granules/{self.granule_id}/mods'
        self.htm_url = f'packages/CREC-{self.date}/granules/{self.granule_id}/htm'

        self.raw_text = ''
        self.clean_text = ''
        self.speakers : Dict[int, Speaker] = {}

        self.passages = TextCollection()
        self.paragraphs = TextCollection()

        self.valid = False

    def __repr__(self) -> str:
        return f'{self.granule_id}'

    def get(self, client = None):
        if isinstance(client, GovInfoClient):
            self.async_get(client=client)
        else:
            mods_response = httpx.get(self.mods_url)
            htm_response = httpx.get(self.htm_url)

            self.parse_responses(mods_response, htm_response)

    async def async_get(self, client: GovInfoClient):
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
            self.speakers[f's{len(self.speakers)}'] = s

    def parse_htm(self, raw_text):
        self.raw_text = raw_text
        text = raw_text

        # remove bullets
        text = re.sub(r'<bullet>', ' ', text)

        # remove title block
        # \n\s+[a-zA-Z1-9\.\-, ]+(?:(?:\r*){2})
        title_block_match = re.search(r'(?<!\n|])\n(?=\n)', text)
        if title_block_match is not None:
            text = text[title_block_match.end():]

        # remove footer
        footer_match = re.search(r'(\n| )+____________________\n+', text)
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
        self.find_passages()

    def find_titled_speakers(self):
        titled_speakers = set()
        for t in TITLES:
            for match in re.findall(t, self.clean_text):
                if match not in titled_speakers:
                    titled_speakers.add(match)
                    s = Speaker.from_title(title=match)
                    self.speakers[f's{len(self.speakers)}'] = s

    def find_passages(self):
        if len(self.speakers) == 0:
            s = UNKNOWN_SPEAKER
            passage = Passage(granule_id=self.granule_id, speaker=s, text=self.clean_text)
            self.passages.add(passage)
            self.paragraphs.merge(passage.paragraphs)
            return

        speaker_search_str = '(' + '|'.join([f'(?P<{s_id}>\n  {s.parsed_name}\. )' for s_id, s in sorted(self.speakers.items(), key=lambda p : len(p[1].parsed_name), reverse=True)]) + ')'
        speaker_matches = list(re.finditer(speaker_search_str, self.clean_text))

        if len(speaker_matches) == 0 or speaker_matches[0].start() > 3:
            if len(self.speakers) == 1:
                s = list(self.speakers.values())[0]
            else:
                s = UNKNOWN_SPEAKER
            end = None if len(speaker_matches) == 0 else speaker_matches[0].start()
            passage = Passage(granule_id=self.granule_id, speaker=s, text=self.clean_text[0:end])
            self.passages.add(passage)
            self.paragraphs.merge(passage.paragraphs)

        for i, match in enumerate(speaker_matches):
            s_id = [k for k, v in match.groupdict().items() if v != None][0]
            speaker = self.speakers[s_id]
            start = match.end()
            end = speaker_matches[i + 1].start() if i < len(speaker_matches) - 1 else None
            passage = Passage(granule_id=self.granule_id, speaker=speaker, text=self.clean_text[start:end])
            self.passages.add(passage)
            self.paragraphs.merge(passage.paragraphs)