'''

ibl.ingest

This package contains 'shadowed' copies of main tables for external data load
most classes here will be defined using
<downstream_module>.RealClass.definition;

Only if some merging/disambiguation will definitions be augmented/modified
locally in some way with additional attributes and/or tables to facillitate the
difference. These differences should still result in tables compatbile with
data copying via insert from select (e.g: Foo.insert(Bar.fetch()))

NOTE:

Since downstream modules involve cross-module definitions, those modules should
be imported as 'ds_module' in order to prevent the possibility of accidental
linkages to downstream tables in the upstream schema.

For example, in the scenario:

  - foo.py defines Foo
  - bar.py defines Bar referencing foo.Foo

  - ingest.bar imports .. foo (for some other reason than foo.Foo)
  - ingest.bar imports .. bar (to get foo.Foo schema string)
  - ingest.bar.Bar.definition = bar.Bar.definition

Setting ingest.bar.Bar.definition = bar.Bar.definition creates an accidental
link to downstream foo.Foo table because 'bar' points to the downstream
module. If foo/bar had been imported as ds_foo/ds_bar instead, the table
definition syntax would not properly resolve any 'foo' in the scope of
ingest.bar and the definition would fail, also failing to create the bad link.



In this scheme, the 'correct' implementation would instead be:

  - foo.py defines Foo
  - bar.py defines Bar referencing foo.Foo

  - ingest.bar imports .. foo as ds_foo (for some other reason than foo.Foo)
  - ingest.bar imports .. bar as ds_bar (to get foo.Foo schema string)
  - ingest.bar imports . foo (to get ingest.foo.Foo)
  - ingest.bar.Bar.definition = bar.Bar.definition

Now, ingest.bar.Bar is able to use bar.Bar.definition, but the definition
of ingest.bar.Bar is resolved within the scope of ingest.bar as pointing to
ingest.foo.Foo, creating the proper link to the ingest related table.

While this should not happen in the current architecture, following the pattern
outlined here should prevent it in general and so is a good 'safe practice' to
use for the ingest modules.
'''
import logging
import datajoint as dj
from . import alyxraw


log = logging.getLogger(__name__)


def get_raw_field(key, field, multiple_entries=False):
    query = alyxraw.AlyxRaw.Field & key & 'fname="{}"'.format(field)
    return query.fetch('fvalue') if multiple_entries else query.fetch1('fvalue')


class InsertBuffer(object):
    '''
    InsertBuffer: a utility class to help managed chunked inserts
    Currently requires records do not have prerequisites.
    '''
    def __init__(self, rel):
        self._rel = rel
        self._queue = []

    def insert1(self, r):
        self._queue.append(r)

    def insert(self, recs):
        self._queue += recs

    def flush(self, replace=False, skip_duplicates=False,
              ignore_extra_fields=False, ignore_errors=False, chunksz=1):
        '''
        flush the buffer
        XXX: use kwargs?
        XXX: ignore_extra_fields na, requires .insert() support
        '''
        qlen = len(self._queue)
        if qlen > 0 and qlen % chunksz == 0:
            try:
                self._rel.insert(self._queue, skip_duplicates=skip_duplicates,
                                 ignore_extra_fields=ignore_extra_fields,
                                 ignore_errors=ignore_errors)
                self._queue.clear()
                return qlen
            except dj.DataJointError as e:
                log.error('error in flush: {}'.format(e))
                raise
        else:
            return 0
