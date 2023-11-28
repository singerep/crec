================
Welcome to crec!
================

**crec** is a python tool built for retrieving, structuring, and enriching the Congressional Record, the official record of the proceedings of the United States Congress. **crec** wraps the GovInfo API — a product of the U.S. Government Publishing Office — with an intuitive and powerful API of its own. 

With **crec**, generating a pandas DataFrame of speech data from the 116th Senate, for example, can be done in just a few lines of code:

>>> from crec import Record
>>> r = Record(start_date="2019-01-03", end_date="2021-01-03", granule_class_filter = ["SENATE"])
INFO:2023-11-13 21:50:14: getting granules with the following classes: ['HOUSE', 'SENATE', 'EXTENSIONS', 'DAILYDIGEST']; skipping granules with the following classes: []
INFO:2023-11-13 21:50:14: getting granules in zipped files in batch 1 of 1
INFO:2023-11-13 21:50:25: successfully got zipped files for 1 of 1 valid dates; there were 0 failures
INFO:2023-11-13 21:50:25: successfully got and parsed 103 of 103 granules; there were 0 failures
>>> r.passages.to_df()
       granuleDate                      granuleId  passage_id                                               text                speaker bioGuideId
0       2019-01-04    CREC-2019-01-04-pt1-PgE11-2           1  Madam Speaker, I rise today to honor Pastor Ke...            Zoe Lofgren    L000397
1       2019-01-04    CREC-2019-01-04-pt1-PgE11-3           1  Madam Speaker, I was not present for Roll Call...      Robert J. Wittman    W000804
2       2019-01-04    CREC-2019-01-04-pt1-PgE11-4           1  Madam Speaker, today is former Congressman Les...       Thomas R. Suozzi    S001201
3       2019-01-04    CREC-2019-01-04-pt1-PgE11-6           1  Madam Speaker, I regret I was unable to vote d...          Lloyd Smucker    S001199
4       2019-01-04    CREC-2019-01-04-pt1-PgE11-7           1  Madam Speaker, I was unavoidably detained due ...             Fred Upton    U000031
..             ...                            ...         ...                                                ...                    ...        ...
320061  2021-01-01    CREC-2021-01-01-pt1-PgS8016           1  Mr. President, I ask unanimous consent that th...           John Boozman    B001236
320062  2021-01-01    CREC-2021-01-01-pt1-PgS8016           2               Without objection, it is so ordered.  The PRESIDING OFFICER       None
320063  2021-01-01  CREC-2021-01-01-pt1-PgS8016-2           1  Mr. President, I ask unanimous consent that wh...           John Boozman    B001236
320064  2021-01-01  CREC-2021-01-01-pt1-PgS8016-2           2               Without objection, it is so ordered.  The PRESIDING OFFICER       None
320065  2021-01-01  CREC-2021-01-01-pt1-PgS8016-3           1  If there is no further business to come before...           John Boozman    B001236

For an brief introduction to **crec**, check out our :doc:`getting started guide <getting_started>`. For an in depth overview of the package, check out the :doc:`API documentation <api>`.

.. toctree::
   :hidden:
   :maxdepth: 2
   
   getting_started
   api