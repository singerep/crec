from xml.etree import ElementTree as et

def parse_single_xml(root: et):
    granule_meta = {
        'parsed_name_map': {}
    }
    granule_id = root.attrib['ID'].split('id-')[1]

    extension = root.find('{http://www.loc.gov/mods/v3}extension')
    members = extension.findall('{http://www.loc.gov/mods/v3}congMember')

    parsed_name_map = {}
    for member in members:
        bioguide_id = member.attrib['bioGuideId']
        names = member.findall('{http://www.loc.gov/mods/v3}name')
        parsed_name = [n for n in names if n.attrib['type'] == 'parsed'][0].text
        parsed_name_map[bioguide_id] = parsed_name
    granule_meta['parsed_name_map'] = parsed_name_map

    return granule_id, granule_meta

def parse_multiple_xml(root: et):
    granule_meta_map = {}

    related_items = [c for c in root if c.tag == '{http://www.loc.gov/mods/v3}relatedItem']

    for item in related_items:
        granule_id, granule_meta = parse_single_xml(item)
        granule_meta_map[granule_id] = granule_meta

def get_granule_roots(root: et):
    return {c.attrib['ID'].split('id-')[1]: c for c in root if c.tag == '{http://www.loc.gov/mods/v3}relatedItem'}
