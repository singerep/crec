from typing import Dict, List
from xml.etree.ElementTree import Element

class Speaker:
    def __init__(self, attributes: Dict[str, str] = None, names: Dict[str, str] = None, titled: bool = False) -> None:
        self.attributes = attributes
        self.names = names
        self.titled = titled

        self.parsed_name = self.names.get('parsed', None)
        self.first_last = self.names.get('authority-fnf', None)

    @classmethod
    def from_title(cls, title: str) -> 'Speaker':
        names = {'parsed': title, 'authority-fnf': title}
        return cls({}, names, True)

    @classmethod
    def from_member(cls, member: Element) -> 'Speaker':
        attributes = member.attrib
        names = {n.attrib['type']: n.text for n in member.findall('{http://www.loc.gov/mods/v3}name')}
        return cls(attributes, names, False)

    def get_attribute(self, attribute: str) -> str:
        return self.attributes.get(attribute, None)

    def __repr__(self) -> str:
        return self.first_last


UNKNOWN_SPEAKER = Speaker.from_title('Unknown')