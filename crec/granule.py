from xml.etree import ElementTree as et
from xml.etree.ElementTree import Element
from collections import defaultdict, namedtuple
import re
import httpx
from typing import List, Dict, Union
import os

from crec.api import GovInfoClient
from crec.speaker import Speaker, UNKNOWN_SPEAKER
from crec.constants import TITLES, GRANULE_ATTRIBUTES
from crec.text import Passage, TextCollection


class Granule:
    def __init__(self, granule_id: str) -> None:
        self.attributes = {}
        self.attributes['granuleId'] = granule_id
        self.mods_url = f'packages/CREC-{granule_id[5:15]}/granules/{granule_id}/mods'
        self.htm_url = f'packages/CREC-{granule_id[5:15]}/granules/{granule_id}/htm'

        self.raw_text = ''
        self.clean_text = ''
        self.speakers : Dict[int, Speaker] = {}

        self.text_collection = TextCollection()

        self.valid_responses = False
        self.parsed = False
        self.written = False
        self.complete = False

        self.parse_exception = None
        self.write_exception = None

    def __repr__(self) -> str:
        raise NotImplementedError

    def get(self, client = None):
        if isinstance(client, GovInfoClient):
            self.async_get(client=client)
        else:
            mods_response = httpx.get(self.mods_url)
            htm_response = httpx.get(self.htm_url)

            self.parse_responses(mods_response, htm_response)

    async def async_get(self, client: GovInfoClient, parse: bool, write: Union[bool, str]):
        mods_response_validity, mods_response = await client.get(self.mods_url)
        htm_response_validity, htm_response = await client.get(self.htm_url)

        if mods_response_validity and htm_response_validity: 
            self.valid_responses = True
            if parse:
                self.parse_responses(mods_response=mods_response, htm_response=htm_response)

            if isinstance(write, str):
                self.write_responses(write=write, mods_response=mods_response, htm_response=htm_response)

        if parse is True and isinstance(write, str):
            if self.parsed and self.written:
                self.complete = True
        elif parse is False and isinstance(write, str):
            if self.written:
                self.complete = True
        elif parse is True and write is False:
            if self.parsed:
                self.complete = True
        else:
            self.complete = True
            
    def parse_responses(self, mods_response: httpx.Response, htm_response: httpx.Response):
        try:
            mods_content = mods_response.content
            root = et.fromstring(mods_content)
            self.parse_xml(root)

            raw_text = htm_response.text
            self.parse_htm(raw_text)

            self.parsed = True
        except Exception as e:
            self.parse_exception = e

    def write_responses(self, write: str, mods_response: httpx.Response, htm_response: httpx.Response):
        try:
            granule_id = self.attributes['granuleId']
            wd = os.getcwd()
            if not os.path.isabs(write):
                xml_path = os.path.join(wd, f'{write}/{granule_id}.xml')
                htm_path = os.path.join(wd, f'{write}/{granule_id}.htm')
            else:
                xml_path = f'{write}/{granule_id}.xml'
                htm_path = f'{write}/{granule_id}.htm'

            with open(xml_path, 'w') as xml_file:
                xml_file.write(mods_response.text)

            with open(htm_path, 'w') as htm_file:
                htm_file.write(htm_response.text)

            self.written = True
        except Exception as e:
            self.write_exception = e

    def parse_xml(self, root: Element):
        for attr in GRANULE_ATTRIBUTES:
            for e in root.iter('{http://www.loc.gov/mods/v3}' + attr):
                self.attributes[attr] = e.text
        
        for member in root.iter('{http://www.loc.gov/mods/v3}congMember'):
            role = member.attrib.get('role', None)
            if role is not None and role == 'SPEAKING':
                s = Speaker.from_member(member=member)
                self.speakers[f's{len(self.speakers)}'] = s

    def parse_htm(self, raw_text):
        self.raw_text = raw_text
        text = raw_text

        # remove bullets
        text = re.sub(r'<bullet>', ' ', text)

        # remove title block
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
            passage = Passage(granule_attributes=self.attributes, speaker=s, text=self.clean_text)
            self.text_collection.add_passage(passage=passage)

        else:
            sorted_speakers = sorted(self.speakers.items(), key=lambda p : len(p[1].parsed_name), reverse=True)
            speaker_search_str = '(' + '|'.join([f'(?P<{s_id}>\n  {s.parsed_name}\. )' for s_id, s in sorted_speakers]) + ')'
            new_speaker_matches = list(re.finditer(speaker_search_str, self.clean_text))

            if len(new_speaker_matches) == 0 or new_speaker_matches[0].start() > 3:
                if len(self.speakers) == 1:
                    s = list(self.speakers.values())[0]
                else:
                    s = UNKNOWN_SPEAKER
                end = None if len(new_speaker_matches) == 0 else new_speaker_matches[0].start()

                passage = Passage(granule_attributes=self.attributes, speaker=s, text=self.clean_text[0:end])
                self.text_collection.add_passage(passage=passage)

            for i, match in enumerate(new_speaker_matches):
                s_id = [k for k, v in match.groupdict().items() if v != None][0]
                speaker = self.speakers[s_id]
                start = match.end()
                end = new_speaker_matches[i + 1].start() if i < len(new_speaker_matches) - 1 else None

                passage = Passage(granule_attributes=self.attributes, speaker=speaker, text=self.clean_text[start:end])
                self.text_collection.add_passage(passage=passage)