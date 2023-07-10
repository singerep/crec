from typing import List, Union
import re
import pandas as pd
import functools

from crec.speaker import Speaker, UNKNOWN_SPEAKER


class Paragraph:
    """
    A class to represent a single paragraph of text from the Congressional Record.

    Parameters
    ----------
    granule_attributes : dict
        A list of attributes associated with the :class:`.Granule` object this paragraph
        is derived from. For a list of possible keys, see :attr:`.Granule.attributes`.
    paragraph_id : int
        An integer indicating the index of this paragraph within the :class:`.Passage`
        it comes from. Starts from 1.
    passage_id : int
        An integer indicating the index of the :class:`.Passage` object this
        paragraph comes from within the :class:`.Granule` it comes from. Starts from 1.
    speaker : :class:`.Speaker`
        The speaker (Member of Congress or titled speaker) that this paragraph belongs
        to.
    speaking : bool
        Indicates whether the speaker was speaking during this paragraph. Options other
        than speaking include notes, quotes, and assorted items entered into the record
        during a passage of speech.
    text : str
        The text of the paragraph. To eliminate extra whitespace, the text is ultimately
        split into tokens and rejoined.
    """
    def __init__(self, granule_attributes: dict, paragraph_id: int, passage_id: int, speaker: Speaker, speaking: bool, text: str) -> None:
        self.granule_attributes = granule_attributes
        self.paragraph_id = paragraph_id
        self.passage_id = passage_id
        self.speaker = speaker
        self.speaking = speaking
        self.text = ' '.join(text.split())

    def __repr__(self) -> str:
        return f'\n---{self} (speaking: {self.speaking})---\n{self.text}'


class Passage:
    """
    A class to represent a single paragraph of text from the Congressional Record.

    Parameters
    ----------
    granule_attributes : dict
        A list of attributes associated with the :class:`.Granule` object this passage
        is derived from. For a list of possible keys, see :attr:`.Granule.attributes`.
    passage_id : int
        An integer indicating the index of this paragraph within the :class:`.Granule`
        it comes from. Starts from 1.
    speaker : :class:`.Speaker`
        The speaker (Member of Congress or titled speaker) that this paragraph belongs
        to.
    speaking : bool
        Indicates whether the speaker was speaking during this passage. For a passage,
        this is always ``True`` because of how the process of finding passages works.
        No new-passage-match is found unless it is the start of someone speaking.
    text : str
        The text of the paragraph. To eliminate extra whitespace, the text is ultimately
        split into tokens and rejoined.

    Attributes
    ----------
    paragraph_collection : :class:`.ParagraphCollection`
        A collection of :class:`.Paragraph` objects that belong to this passage.
    clean_text : str
        The concatenation of the clean text of all of the paragraphs associated with
        this paragraph, separated by newlines.
    """
    
    def __init__(self, granule_attributes: dict, passage_id : int, speaker: Speaker, speaking: bool = True, text: str = '') -> None:
        self.granule_attributes = granule_attributes
        self.passage_id = passage_id
        self.speaker = speaker
        self.speaking = speaking
        self.text = f'\n  {text}'

        self._paragraph_collection = ParagraphCollection()
        self.split_into_paragraphs()

        self.text = ' '.join(self.text.split())

    def __repr__(self) -> str:
        return f'---{self.speaker}---\n' + self.clean_text

    def split_into_paragraphs(self):
        """
        Splits the passage's text into :class:`.Paragraph` objects. The Congressional
        Record generally indicates a paragraph break with a newline followed by two
        spaces, but in cases where a new paragraph is beginning where *no one is
        speaking*, such as bill being entered into the record, the text is typically
        extra indented (more spaces).

        This function uses that pattern and splits the passage on those two types of
        paragraph breaks. This results in a list of paragraph breaks, and checking
        which pattern matched to the break tells the function whether the given 
        paragraph is spoken or not.
        """
        p_breaks = list(re.finditer(r'(?P<speaking>\n  (?! ))|(?P<nonspeaking>\n\n   +)', self.text))
        for i, match in enumerate(p_breaks):
            speaking = [k for k, v in match.groupdict().items() if v != None][0] == 'speaking'
            p_start = match.end()
            p_end = p_breaks[i + 1].start() if i < len(p_breaks) - 1 else None
            paragraph = Paragraph(granule_attributes=self.granule_attributes, paragraph_id=i + 1, passage_id=self.passage_id, speaker=self.speaker, speaking=speaking, text=self.text[p_start:p_end])
            self._paragraph_collection.add(paragraph)

    @property
    def paragraphs(self):
        return self._paragraph_collection
    
    @property
    def clean_text(self):
        return '\n'.join([p.text for p in self.paragraphs._paragraphs])


class ParagraphCollection:
    """
    A collection of :class:`.Paragraph` objects.

    Attributes
    ----------
    paragraphs : List[:class:`.Paragraph`]
        A list of paragraph objects.
    """
    def __init__(self) -> None:
        self._paragraphs : List[Paragraph] = []

    def merge(self, other: 'ParagraphCollection') -> None:
        """
        Merges another :class:`.ParagraphCollection` with itself by concatenating
        the two :attr:`.ParagraphCollection.paragraphs` lists together.
        """
        self._paragraphs += other._paragraphs

    def add(self, paragraph: Paragraph):
        """
        Adds a single :class:`.Paragraph` object to 
        :attr:`.ParagraphCollection.paragraphs`.
        """
        self._paragraphs.append(paragraph)

    def to_list(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, search: str = None) -> List[Paragraph]:
        """
        Returns a list of :class:`.Paragraph` objects that meet the desired criteria.

        Parameters
        ----------
        include_unknown_speakers : bool = False
            Occasionally, a :class:`.Granule` finds passages and paragraphs with 
            no known speaker. This parameter controls whether such paragraphs should be
            kept or filtered out.
        include_non_speaking : bool = False
            This parameter controls whether the output should include paragraphs that
            are not spoken, as determined by the type of match in 
            :meth:`.Passage.split_into_paragraphs()`.
        search : str = None
            If provided, only paragraphs whose text contain ``search`` (ignoring case)
            are included.
        """
        valid_paragraphs = []
        for paragraph in self._paragraphs:
            if include_unknown_speakers is False and paragraph.speaker == UNKNOWN_SPEAKER:
                continue
            if include_non_speaking is False and paragraph.speaking is False:
                continue
            if search is not None and search.lower() not in paragraph.text.lower():
                continue

            valid_paragraphs.append(paragraph)

        return valid_paragraphs

    def to_df(self, include_unknown_speakers: bool = False, include_non_speaking: bool = False, granule_attributes: List[str] = ['granuleDate', 'granuleId'], speaker_attributes: List[str] = ['bioGuideId'], search: str = None) -> pd.DataFrame:
        """
        Construct and return a :class:`pd.DataFrame` object from paragraphs that 
        meet the desired criteria.

        Parameters
        ----------
        include_unknown_speakers : bool = False
            Occasionally, a :class:`.Granule` finds passages and paragraphs with 
            no known speaker. This parameter controls whether such paragraphs should be
            kept or filtered out.
        include_non_speaking : bool = False
            This parameter controls whether the output should include paragraphs that
            are not spoken, as determined by the type of match in 
            :meth:`.Passage.split_into_paragraphs()`.
        granule_attributes : List[str] = [`granuleId`]
            Each entry in this list will be an additional column in the final
            :class:`pd.DataFrame`. For a full list of options, see
            :attr:`.Granule.attributes`.
        speaker_attributes : List[str] = [`bioGuideId`]
            Each entry in this list will be an additional column in the final
            :class:`pd.DataFrame`. For a full list of options, see
            :attr:`.Speaker.attributes`.
        search : str = None
            If provided, only paragraphs whose text contain ``search`` (ignoring case)
            are included.
        """
        valid_paragraphs = self.to_list(include_unknown_speakers=include_unknown_speakers, include_non_speaking=include_non_speaking, search=search)
        paragraph_dicts = []
        for paragraph in valid_paragraphs:
            paragraph_dict = {}
            for attr in granule_attributes:
                paragraph_dict[attr] = paragraph.granule_attributes.get(attr, None)

            paragraph_dict['passage_id'] = paragraph.passage_id
            paragraph_dict['paragraph_id'] = paragraph.paragraph_id
            paragraph_dict['text'] = paragraph.text
            paragraph_dict['speaker'] = paragraph.speaker.first_last
            paragraph_dict['speaking'] = paragraph.speaking
            
            for attr in speaker_attributes:
                paragraph_dict[attr] = paragraph.speaker.get_attribute(attr)
            paragraph_dicts.append(paragraph_dict)

        return pd.DataFrame(paragraph_dicts)


class PassageCollection:
    """
    A collection of :class:`.Paragraph` objects.

    Attributes
    ----------
    passages : List[:class:`.Passage`]
        A list of passage objects.
    paragraphs : :class:`.ParagraphCollection`
        Stores the :class:`.Paragraph` objects associated with this passage.
    """
    def __init__(self) -> None:
        self._passages : List[Passage] = []

    def merge(self, other: 'PassageCollection') -> None:
        """
        Merges another :class:`.PassageCollection` with itself by concatenating
        the two :attr:`.PassageCollection.passages` lists together.
        """
        self._passages += other._passages

    def add(self, passage: Passage):
        """
        Adds a single :class:`.Passage` object to :attr:`.PassageCollection.passages`.
        """
        self._passages.append(passage)

    def to_list(self, include_unknown_speakers: bool = False, search: str = None) -> List[Passage]:
        """
        Returns a list of :class:`.Passage` objects that meet the desired criteria.

        Parameters
        ----------
        include_unknown_speakers : bool = False
            Occasionally, a :class:`.Granule` finds passages and paragraphs with 
            no known speaker. This parameter controls whether such paragraphs should be
            kept or filtered out.
        search : str = None
            If provided, only paragraphs whose text contain ``search`` (ignoring case)
            are included.
        """
        valid_passages = []
        for passage in self._passages:
            if include_unknown_speakers is False and passage.speaker == UNKNOWN_SPEAKER:
                continue
            if search is not None and search.lower() not in passage.text.lower():
                continue

            valid_passages.append(passage)

        return valid_passages

    def to_df(self, include_unknown_speakers: bool = False, granule_attributes: List[str] = ['granuleId'], speaker_attributes: List[str] = ['bioGuideId'], search: str = None) -> pd.DataFrame:
        """
        Construct and return a :class:`pd.DataFrame` object from passages that 
        meet the desired criteria.

        Parameters
        ----------
        include_unknown_speakers : bool = False
            Occasionally, a :class:`.Granule` finds passages and paragraphs with 
            no known speaker. This parameter controls whether such paragraphs should be
            kept or filtered out.
        granule_attributes : List[str] = [`granuleId`]
            Each entry in this list will be an additional column in the final
            :class:`pd.DataFrame`. For a full list of options, see
            :attr:`.Granule.attributes`.
        speaker_attributes : List[str] = [`bioGuideId`]
            Each entry in this list will be an additional column in the final
            :class:`pd.DataFrame`. For a full list of options, see
            :attr:`.Speaker.attributes`.
        search : str = None
            If provided, only paragraphs whose text contain ``search`` (ignoring case)
            are included.
        """
        valid_passages = self.to_list(include_unknown_speakers=include_unknown_speakers, search=search)
        passage_dicts = []
        for passage in valid_passages:
            passage_dict = {}
            for attr in granule_attributes:
                passage_dict[attr] = passage.granule_attributes.get(attr, None)

            passage_dict['passage_id'] = passage.passage_id
            passage_dict['text'] = passage.text
            passage_dict['speaker'] = passage.speaker.first_last
            
            for attr in speaker_attributes:
                passage_dict[attr] = passage.speaker.get_attribute(attr)
            
            passage_dicts.append(passage_dict)

        return pd.DataFrame(passage_dicts)

    @property
    def paragraphs(self):
        collection = ParagraphCollection()
        for passage in self._passages:
            collection.merge(passage.paragraphs)
        return collection