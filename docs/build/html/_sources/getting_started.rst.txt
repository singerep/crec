===============
Getting started
===============

------------
Installation
------------

--------
Tutorial
--------

Before reading on, it may be helpful to check out the `GovInfo API <https://api.govinfo.gov/docs/>`_ itself.

^^^^^^^^^^^^
Getting data
^^^^^^^^^^^^

To fetch data using **crec**, start by creating a :class:`.Record` object. There are three ways to do so.

1. By providing a ``start_date`` and an ``end_date``.

>>> r = Record(start_date="2019-01-03", end_date="2021-01-03")

2. By providing a list of ``dates``.

>>> r = Record(dates=["2019-01-03", "2020-01-03", "2021-01-03"])

3. By providing a list of ``granule_ids``. Granule identifiers can be obtained and filtered by using GovInfo's `Advanced Search <https://www.govinfo.gov/help/searching>`_ functionality.

>>> r = Record(granule_ids=["CREC-2020-12-28-pt1-PgE1207-2", "CREC-2020-12-28-pt1-PgE1207-3", "CREC-2020-12-28-pt1-PgE1208"])

There are a number of additional parameters you can provide when creating a record. For example, you can restrict the record to an individual chamber. If you're not interested in parsing the text data, you can choose to write the text and xml files that come from the GovInfo API to disk instead. There are also parameters that control how quickly data should be requested, and what to do in the case that an error occurs. Finally, you can control how **crec** will produce and output logs. For a full overview of these parameters, check out :class:`.Record` in the API documentation.

^^^^^^^^^^^^^^
Analyzing data
^^^^^^^^^^^^^^

To interact with data retrieved by the :class:`.Record`, you'll mostly interact with the :attr:`.Record.passages` or :attr:`.Record.paragraphs` attribute, which holds all of the parsed, cleaned, and annotated text data at the passage and paragraph level, respectively. To read more about these, check out the :class:`.PassageCollection` and :class:`.ParagraphCollection` sections of the API documentation.

To view passages in the format of a :class:`pandas.DataFrame`, simply call:

>>> r.passages.to_df()

This will, by default, return a DataFrame of consisting of data from the :class:`.PassageCollection` object associated with the record. If you'd rather look at paragraphs, change the call to:

>>> r.paragraphs.to_df()

As is, the resulting DataFrame will have the following columns: ``granuleDate``, ``granuleId``, ``passage_id``, ``paragraph_id``, ``text``, ``speaker``, and ``bioGuideId``. You can choose to add additional parameters describing both the granule (eg. ``searchTitle`` and ``granuleClass``) and the speaker (eg. ``party`` and ``state``) associated with each text element. Constructing a DataFrame with all available parameters would look like this:

>>> r.text_collection.to_df(
    granule_attributes = ['searchTitle', 'granuleClass', 'subGranuleClass', 'chamber', 'granuleDate'],
    speaker_attributes = ['authorityId', 'bioGuideId', 'chamber', 'congress', 'gpoId', 'party', 'role', 'state']
)

You can use any and all :class:`pandas.DataFrame` attributes and methods to analyze the record's data.

For example, to see which Senators use the word "education" the most, you could do something like this:

>>> r.passages.to_df().groupby("bioGuideId").apply(lambda group : len(group[group["text"].contains("education")]))

If you want to interact with the :class:`.Passage` or :class:`.Paragraph` objects themselves, you can use something like the following instead:

>>> r.passages.to_list()

Feel free to play around!