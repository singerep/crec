from xml.etree import ElementTree as et
from xml.etree.ElementTree import Element
import re
import httpx
from typing import List, Dict, Tuple, Union
import os
import math
import functools

from crec.api import GovInfoClient
from crec.speaker import Speaker, UNKNOWN_SPEAKER
from crec.constants import TITLES, GRANULE_ATTRIBUTES
from crec.text import Passage, PassageCollection, ParagraphCollection
from crec.logger import Logger

async def get_granule_ids(date: str, client: GovInfoClient, granule_class_filters: List[str], logger: Logger) -> Tuple[bool, List[str]]:
    """
    A function to retrieve the granule identifiers associated with a specific day.
    Takes as an input a date string, a :class:`.GovInfoClient` object, a list of 
    granule_class_filters, and a :class:`.Logger` object.
    
    This function reaches the ``/granules`` endpoint of the GovInfo API which returns these
    identifiers. If provided, only granules with a class listed in 
    ``granule_class_filter`` will be retrieved. Otherwise, all granules are included.
    """
    logger.log(f'getting granule ids from {date}')
    got_all_ids = False

    granules_url = f'packages/CREC-{date}/granules'

    granules_resp_validity, granules_resp = await client.get(granules_url, params={'offset': '0', 'pageSize': '100'})
    if granules_resp_validity:
        got_all_ids = True
    else:
        return []
    
    granules_json = granules_resp.json()
    
    granules_count = granules_json['count']
    granule_ids = [g['granuleId'] for g in granules_json['granules'] if g['granuleClass'] in granule_class_filters]

    if granules_count > 100:
        got_all_ids = False
        remaining_pages = math.ceil((granules_count - 100)/100)
        for p in range(1, remaining_pages + 1):
            offset = 100*p
            next_granules_resp_validity, next_granules_resp = await client.get(granules_url, params={'offset': f'{offset}', 'pageSize': '100'})
            if next_granules_resp_validity:
                pass
            else:
                break
            next_granules_json = next_granules_resp.json()
            granule_ids += [g['granuleId'] for g in next_granules_json['granules'] if g['granuleClass'] in granule_class_filters]
        got_all_ids = True
    
    return got_all_ids, granule_ids


class Granule:
    """
    Represents a single GovInfo granule and its associated metadata and text.

    Parameters
    ----------
    granule_id : str
        The granule's identifier

    Attributes
    ----------
    attributes : dict
        A dictionary of information describing the granule. Possible keys are:

        * ``granuleDate``
        * ``granuleId``
        * ``searchTitle``
        * ``granuleClass``
        * ``subGranuleClass``
        * ``chamber``
    
    xml_url : str
        A relative URL that reaches the ``/mods`` endpoint of the GovInfo API to
        request the granule's metadata.
    htm_url : str
        A relative URL that reaches the ``/htm`` endpoint of the GovInfo API to
        request the granule's text.
    raw_text : str
        The text of the granule without elements like headers, page numbers, 
        and times removed.
    clean_text : str
        The text of the granule with elements like headers, page numbers, 
        and times removed.
    speakers : Dict[str, speaker]
        A mapping between speaker identifiers and :class:`.Speaker` objects for all of 
        the speakers on the granule, including speakers referred to by title only 
        (ie. The PRESIDENT pro tempore).
    valid_responses : bool
        A boolean that indicates whether the metadata and text requests both
        properly resolved.
    parsed : bool
        A boolean that indicates whether the text of the granule was successfully
        parsed.
    written : bool
        A boolean that indicates whether the metadata and text of the granule 
        were successfully written to disk.
    complete : bool
        A boolean that indicates whether the desired behavior (parsing and writing)
        was achieved. If both ``parse`` and ``write`` are ``True``, then ``parsed``
        and ``written`` must be ``True`` for the granule to be ``complete``; if
        ``parse`` is ``True`` and ``write`` is ``False``, only ``parsed`` must be true
        for the granule to be ``complete``; if ``parse`` is ``False`` and ``write`` 
        is ``True``, only ``written`` must be true for the granule to be ``complete``.
        Finally, if both ``parse`` and ``write`` are ``False``, the granule is 
        automatically ``complete``.
    parse_exception : Exception
        In the case of a parsing exception, that exception is assigned to this
        attribute.
    write_exception : Exception
        In the case of a writing exception, that exception is assigned to this
        attribute.
    passages : :class:`.PassageCollection`
        Stores the :class:`.Passage` objects associated with this granule.
    paragraphs : :class:`.ParagraphCollection`
        Stores the :class:`.Paragraph` objects associated with this granule.
    """
    def __init__(self, granule_id: str) -> None:
        self.id = granule_id
        self.attributes = {}
        self.attributes['granuleId'] = granule_id
        self.xml_url = f'packages/CREC-{granule_id[5:15]}/granules/{granule_id}/mods'
        self.htm_url = f'packages/CREC-{granule_id[5:15]}/granules/{granule_id}/htm'

        self.raw_text = ''
        self.clean_text = ''
        self.speakers : Dict[str, Speaker] = {}

        self._passage_collection = PassageCollection()

        self.valid_responses = False
        self.parsed = False
        self.written = False
        self.complete = False

        self.parse_exception = None
        self.write_exception = None

    def __repr__(self) -> str:
        return f'Granule (id: {self.id})'

    async def async_get(self, client: GovInfoClient, parse: bool, write: Union[bool, str]) -> None:
        """
        Takes as an input a :class:`.GovInfoClient` object, and booleans indicating
        whether the granule's data should be parsed and/or written to disk. Requests
        the granule's metadata and text, and proceeds from there.
        """
        xml_response_validity, xml_response = await client.get(self.xml_url)
        htm_response_validity, htm_response = await client.get(self.htm_url)

        if xml_response_validity and htm_response_validity: 
            self.valid_responses = True
            if parse:
                self.parse_responses(xml_response=xml_response, htm_response=htm_response)

            if isinstance(write, str):
                self.write_responses(write=write, xml_response=xml_response, htm_response=htm_response)

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
            
    def parse_responses(self, xml_response: Union[httpx.Response, Element], htm_response: Union[httpx.Response, str]) -> None:
        """
        Takes both the metadata (xml) and text (htm) responses return from the
        :class:`.GovInfoClient` object. Tries to parse both of them. In the case of an
        error, saves the error to either the :attr:`.Granule.parse_exception`
        attribute.
        """
        try:
            if isinstance(xml_response, httpx.Response):
                xml_content = xml_response.content
                root = et.fromstring(xml_content)
            else:
                root = xml_response
            self.parse_xml(root)

            if isinstance(htm_response, httpx.Response):
                raw_text = htm_response.text
            else:
                raw_text = htm_response
            self.parse_htm(raw_text)

            self.parsed = True
        except Exception as e:
            self.parse_exception = e

    def write_responses(self, write: str, xml_response: Union[httpx.Response, Element], htm_response: Union[httpx.Response, str]) -> None:
        """
        Takes a ``write`` path, and both the metadata (xml) and text (htm) responses return from the
        :class:`.GovInfoClient` object. Tries to write both of them to disk. In the 
        case of an error, saves the error to either the :attr:`.Granule.write_exception`
        attribute.
        """
        try:
            granule_id = self.attributes['granuleId']
            wd = os.getcwd()
            if not os.path.isabs(write):
                xml_path = os.path.join(wd, f'{write}/{granule_id}.xml')
                htm_path = os.path.join(wd, f'{write}/{granule_id}.htm')
            else:
                xml_path = f'{write}/{granule_id}.xml'
                htm_path = f'{write}/{granule_id}.htm'

            if isinstance(xml_response, httpx.Response):
                xml_text = xml_response.text
            else:
                xml_text = et.tostring(xml_response, encoding='unicode')

            if isinstance(htm_response, httpx.Response):
                htm_text = htm_response.text
            else:
                htm_text = htm_response

            with open(xml_path, 'w') as xml_file:
                xml_file.write(xml_text)

            with open(htm_path, 'w') as htm_file:
                htm_file.write(htm_text)

            self.written = True
        except Exception as e:
            self.write_exception = e

    def parse_xml(self, root: Element) -> None:
        """
        Parses the xml response. First, it updates the :attr:`.Granule.attributes` 
        dictionary. Then, it finds all listed Congress Members who spoke during the
        course of the granule. For each one, it instantiates a :class:`.Speaker`
        object, and a unique speaker identifier, and adds those to the granule's
        mapping of speakers.
        """

        for attr in GRANULE_ATTRIBUTES:
            for e in root.iter('{http://www.loc.gov/mods/v3}' + attr):
                self.attributes[attr] = e.text
        
        for member in root.iter('{http://www.loc.gov/mods/v3}congMember'):
            role = member.attrib.get('role', None)
            has_parsed = any([name.attrib.get('type', None) == 'parsed' for name in member.findall('{http://www.loc.gov/mods/v3}name')])
            if role is not None and role == 'SPEAKING' and has_parsed is True:
                s = Speaker.from_member(member=member)
                self.speakers[f's{len(self.speakers)}'] = s
            if role is not None and role != 'SPEAKING' and 'VOTING' not in role and 'VOTED' not in role:
                print(role)

    def parse_htm(self, raw_text) -> None:
        """
        Parses the text response. Starts by removing common non-speech elements:
        the title, the footer, page numbers, and times. Then, it calls the
        :meth:`.Granule.find_titled_speakers()` and :meth:`.Granule.find_passages()`
        functions.
        """
        self.raw_text = raw_text
        text = raw_text

        # remove bullets
        text = re.sub(r'<bullet>', ' ', text)

        # remove title block
        title_block_match = re.search(r'(?<!\s)\n\n(  )(?!\s)', text)
        if title_block_match is not None:
            text = '\n  ' + text[title_block_match.end():]

        # remove footer
        footer_match = re.search(r'(\n| )+____________________\n+', text)
        if footer_match is not None:
            text = text[:footer_match.start()]

        # remove inline page numbers
        text = re.sub('\n\n\[\[Page .+\]\n\n(?=[a-zA-Z0-9])', ' ', text)

        # remove other page numbers
        text = re.sub('\[\[Page .+\]\]', '', text)

        # remove times
        text = re.sub('\{time\}\s+\d+', '', text)

        # remove notes
        text = re.sub('\n+ =+ NOTE =+(.|\n)+ END NOTE =+', '\n  ', text)

        # remove bottom html
        bottom_html_match = re.search('\n+<\/pre><\/body>\n<\/html>', text)
        if bottom_html_match is not None:
            text = text[:bottom_html_match.start() + 1]

        spoken_paragraphs = re.finditer('((?<=(\n  ))|(?<=(\n   )))(?P<text>[^\s\(\[][\s\S]*?)(?=(\n  )|(\Z))', text)
        text = '\n\n'.join([p.group('text') for p in spoken_paragraphs])

        self.clean_text = text

        self.find_titled_speakers()
        self.find_passages()

    def find_titled_speakers(self) -> None:
        """
        Searches through the cleaned text to find instances of 'titled speakers,' or
        a speaker who is not listed in the xml and is only referred to by title.
        Examples of this type of speaker include The PRESIDING OFFICER and
        The CHIEF JUSTICE. For each titled speaker, it creates a new :class:`.Speaker`
        object, and a unique speaker identifier, and adds those to the granule's
        mapping of speakers.
        """
        titled_speakers = set()
        for t in TITLES:
            for match in re.findall(t, self.clean_text):
                if match not in titled_speakers:
                    titled_speakers.add(match)
                    s = Speaker.from_title(title=match)
                    self.speakers[f's{len(self.speakers)}'] = s

    def find_passages(self) -> None:
        """
        Splits the cleaned text into :class:`.Passage` objects. This process goes as
        follows:

        First, the function checks the length of the :attr:`.speaker` attribute. If the
        length is zero, there are no known speakers. As such, the entire cleaned text
        is assigned to a single :class:`.Passage` with an unknown speaker.

        If there is more than one speaker, the function continues. The idea here is to
        take advantage of the ways the Congressional Record introduces new speakers. 
        For Members of Congress, the Congressional Record places their honorific 
        (Mr., Ms., Dr., etc.) and their fully capitalized last name at the beginning
        of the paragraph where they begin speaking. 
        
        An example may look like this:

        .. code-block:: text

              Ms. TENNEY. Mr. Speaker, I rise today to recognize a new record in 
            Oswego County, New York. The town of Redfield now has the record for 
            the most snowfall in 48 hours. An astonishing 62 inches of snow fell in 
            this idyllic town along the Salmon River with only 550 people near Lake 
            Ontario.

        Or this:

        .. code-block:: text

              Mr. McCONNELL. Mr. President, I ask unanimous consent that the Senate 
            proceed to legislative session for a period of morning business, with 
            Senators permitted to speak therein for up to 10 minutes each.

        Notice that the last name is not always fully capitalized. There are some other
        inconsistencies as well. Some examples include:

        * Mr. RODNEY DAVIS of Illinois.
        * Ms. ROS-LEHTINEN.

        Finally, titled speakers follow slightly different patterns. Examples include:

        * The SPEAKER pro tempore.
        * The CHIEF JUSTICE.
        * Mr. Manager RASKIN.

        Thankfully, the metadata of each granule lists the "parsed name" of each 
        speaking Member of Congress, or how their name will appear in the text when 
        they begin speaking. These parsed names are assigned to the appropriate
        :class:`.Speaker` objects when :meth:`.Granule.parse_xml()` is called. 
        
        Similarly, the parsed names of titled speakers are found and assigned when
        :meth:`.Granule.find_titled_speakers()` is called.
        
        These parsed names are used to construct a regex search string that can 
        identify new speakers at the beginning of paragraphs. The function splits the 
        cleaned text up at these new-speaker-matches, and assigns each piece of text to
        a :class:`.Passage` object attributed to the corresponding speaker.
        """
        passage_id = 1
        if len(self.speakers) == 0:
            s = UNKNOWN_SPEAKER
            passage = Passage(granule_attributes=self.attributes, passage_id=passage_id, speaker=s, text=self.clean_text)
            self._passage_collection.add(passage=passage)
        else:
            sorted_speakers = sorted(self.speakers.items(), key=lambda p : len(p[1].parsed_name), reverse=True)
            speaker_search_str = '(' + '|'.join([f'(?P<{s_id}>{s.re_search}(\.| led the Pledge of Allegiance as follows:| \(for [\s\S]+\):)( |))' for s_id, s in sorted_speakers]) + ')'
            new_speaker_matches = list(re.finditer(speaker_search_str, self.clean_text))

            if len(new_speaker_matches) == 0 or new_speaker_matches[0].start() > 3:
                if re.match('(^SA \d+\.)|(^S. \d+\.)', self.clean_text):
                    if len(new_speaker_matches) == 0:
                        return
                    else:
                        pass
                else:
                    if len(self.speakers) == 1:
                        s = list(self.speakers.values())[0]
                    else:
                        s = UNKNOWN_SPEAKER
                    end = None if len(new_speaker_matches) == 0 else new_speaker_matches[0].start()

                    passage = Passage(granule_attributes=self.attributes, passage_id=passage_id, speaker=s, text=self.clean_text[0:end])
                    passage_id += 1
                    self._passage_collection.add(passage=passage)

            for i, match in enumerate(new_speaker_matches):
                s_id = [k for k, v in match.groupdict().items() if v != None][0]
                speaker = self.speakers[s_id]
                start = match.end()
                end = new_speaker_matches[i + 1].start() if i < len(new_speaker_matches) - 1 else None

                passage = Passage(granule_attributes=self.attributes, passage_id=passage_id, speaker=speaker, text=self.clean_text[start:end])
                passage_id += 1
                self._passage_collection.add(passage=passage)

    @property
    def passages(self) -> PassageCollection:
        return self._passage_collection

    @property
    def paragraphs(self) -> ParagraphCollection:
        return self._passage_collection.paragraphs