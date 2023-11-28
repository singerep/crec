TITLES = [
    'The PRESIDING OFFICER(?: \([^)]*\))?',
    'The SPEAKER pro tempore(?: \([^)]*\))?(?: \(during the vote\))?',
    'The SPEAKER pro tempore(?: \(during the vote\))?',
    'The SPEAKER pro tempore(?: \([^)]*\))?',
    'The SPEAKER pro tempore',
    'The SPEAKER(?: \(during the vote\))',
    'The SPEAKER(?: \([^)]*\))?',
    'The CHAIR(?: \([^)]*\))?',
    'The Acting CHAIR(?: \([^)]*\))?',
    'The ACTING PRESIDENT pro tempore',
    'The ACTING PRESIDENT(?: \([^)]*\))?',
    'The PRESIDENT(?: \([^)]*\))?',
    'The CHIEF JUSTICE(?: \([^)]*\))?',
    'The VICE PRESIDENT(?: \([^)]*\))?',
    '(Mr\.|Ms\.|Miss) Counsel (?=\w*[A-Z]{2,})[A-Za-z]{3,}',
    '(Mr\.|Ms\.|Miss) Manager (?=\w*[A-Z]{2,})[A-Za-z]{3,}'
]

GRANULE_CLASSES = ['HOUSE', 'SENATE', 'EXTENSIONS', 'DAILYDIGEST']
GRANULE_ATTRIBUTES = ['granuleDate',  'granuleId', 'searchTitle', 'granuleClass', 'subGranuleClass', 'chamber']
SPEAKER_ATTRIBUTES = ['authorityId', 'bioGuideId', 'chamber', 'congress', 'gpoId', 'party', 'role', 'state']

ATTRIBUTES = {
    'granule': GRANULE_ATTRIBUTES,
    'speaker': SPEAKER_ATTRIBUTES
}