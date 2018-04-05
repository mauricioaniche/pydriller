import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

from dateutil import tz
from pydriller.repository_mining import RepositoryMining

from datetime import datetime


def test_one_timezone():
    lc = list(RepositoryMining('test-repos/git-2/', single='29e929fbc5dc6a2e9c620069b24e2a143af4285f').traverse_commits())

    to_zone = tz.gettz('GMT+2')
    dt = datetime(2016, 4, 4, 13, 21, 25, tzinfo=to_zone)

    assert dt == lc[0].author_date


def test_between_dates_reversed():
    lc = list(
        RepositoryMining('test-repos/git-4/', single='375de7a8275ecdc0b28dc8de2568f47241f443e9').traverse_commits())

    to_zone = tz.gettz('GMT-4')
    dt = datetime(2016, 10, 8, 17, 57, 49, tzinfo=to_zone)

    assert dt == lc[0].author_date