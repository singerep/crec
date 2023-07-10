================
Welcome to crec!
================

**crec** is a python tool that facilitates scraping, parsing, and processing text from the Congressional Record, the official record of the proceedings of the United States Congress. **crec** wraps the GovInfo API — a product of the U.S. Government Publishing Office — with an intuitive and powerful API of its own. 

With **crec**, generating a pandas DataFrame of speech data from the 116th Senate, for example, can be done in just a few lines of code.

>>> from crec import Record
>>> r = Record(start_date="2019-01-03", end_date="2021-01-03", granule_class_filter = ["SENATE"])
>>> r.text_collection.to_df()
                           granuleId                         text                speaker  bioGuideId
0          CREC-2019-01-04-pt1-PgS33  Under the previous order...  The PRESIDING OFFICER        None
1        CREC-2019-01-04-pt1-PgS32-4     Mr. President, as we ...     Charles E. Schumer     S000148
2        CREC-2019-01-04-pt1-PgS32-3     The Democratic leader...  The PRESIDING OFFICER        None
                                 ...                          ...                    ...         ...
29471  CREC-2021-01-01-pt1-PgS7995-6  Under the previous order...  The PRESIDING OFFICER        None
29472  CREC-2021-01-01-pt1-PgS7995-5   Mr. President, I move t...        Mitch McConnell     M000355
29473  CREC-2021-01-01-pt1-PgS7995-5  The clerk will report th...  The PRESIDING OFFICER        None

For an brief introduction to **crec**, check out our :doc:`getting started guide <getting_started>`. For an in depth overview of the package, check out the :doc:`API documentation <api>`.

.. toctree::
   :hidden:
   :maxdepth: 2
   
   getting_started
   api


.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
