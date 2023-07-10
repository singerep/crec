from typing import Dict, List
from xml.etree.ElementTree import Element

class Speaker:
    """
    A class to represent a single speaker -- either a Member of Congress or a titled
    speaker.

    Parameters
    ----------
    attributes : Dict[str, str] = None
        A dictionary of attributes that describe the speaker. Possible keys are:

        * ``authorityId``
        * ``bioGuideId``
        * ``chamber``
        * ``congress``
        * ``gpoId``
        * ``party``
        * ``role``
        * ``state``

    names : Dict[str, str] = None
        A dictionary of names the speaker goes by. Possible keys are:

        * ``parsed``
        * ``authority-fnf`` (First Last)
        * ``authority-lnf`` (Last, First)

    titled : bool = False
        A boolean indicating whether the speaker is a titled speaker 
        (President pro tempore, Chief Justice, etc.), and not a Member of Congress.
    """
    def __init__(self, attributes: Dict[str, str] = None, names: Dict[str, str] = None, titled: bool = False) -> None:
        self.attributes = attributes
        self.names = names
        self.titled = titled

        self.parsed_name = self.names.get('parsed', None)
        self.first_last = self.names.get('authority-fnf', None)

    @classmethod
    def from_title(cls, title: str) -> 'Speaker':
        """
        This classmethod instantiates a :class:`.Speaker` object from a title alone.
        The provided title is set to be both the parsed and first-last name of the
        speaker.

        Parameters
        ----------
        title : str
            The name of the speaker.
        """
        names = {'parsed': title, 'authority-fnf': title}
        return cls({}, names, True)

    @classmethod
    def from_member(cls, member: Element) -> 'Speaker':
        """
        This classmethod instantiates a :class:`.Speaker` object to represent a 
        Member of Congress. The Member's attributes and names are assigned to the
        speaker's attributes and names.

        Parameters
        ----------
        member : xml.etree.ElementTree.Element
            An xml element that represents a Member of Congress.
        """
        attributes = member.attrib
        names = {n.attrib['type']: n.text for n in member.findall('{http://www.loc.gov/mods/v3}name')}
        return cls(attributes, names, False)

    def get_attribute(self, attribute: str) -> str:
        """
        Returns the requested speaker attribute if it exists; otherwise, returns 
        ``None``.
        """
        return self.attributes.get(attribute, None)

    def __repr__(self) -> str:
        return self.first_last


UNKNOWN_SPEAKER = Speaker.from_title('Unknown')