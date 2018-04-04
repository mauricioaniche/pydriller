import os
import psutil
if 'TRAVIS' in os.environ:
    import logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

from pydriller.domain.commit import Commit
from pydriller.repository_mining import RepositoryMining
from pydriller.scm.commit_visitor import CommitVisitor
from pydriller.scm.git_repository import GitRepository
from pydriller.scm.persistence_mechanism import PersistenceMechanism
from datetime import datetime


def test_memory():
    if 'TRAVIS' not in os.environ:
        return

    mv = MemoryVisitor()

    start = datetime.now()
    RepositoryMining('test-repos/rails', mv,
                     from_commit='977b4be208c2c54eeaaf7b46953174ef402f49d4',
                     to_commit='ede505592cfab0212e53ca8ad1c38026a7b5d042').mine()
    end = datetime.now()

    diff = end - start
    logging.info('Max memory {} Mb'.format(max(mv.all)))
    logging.info('Min memory {} Mb'.format(min(mv.all)))
    logging.info('All: {}'.format(', '.join(map(str, mv.all))))
    logging.info('Time {}:{}:{}'.format(diff.seconds//3600, (diff.seconds % 3600) // 60, diff.seconds % 60))
    logging.info('Commits per second: {}'.format(len(mv.all) / diff.seconds))


class MemoryVisitor(CommitVisitor):
    def __init__(self):
        self.p = psutil.Process(os.getpid())
        self.numberOfCommits = 0
        self.all = []

    def process(self, repo: GitRepository, commit: Commit, writer: PersistenceMechanism):
        memory = self.p.memory_info()[0] / (2 ** 20)
        self.all.append(memory)
        self.numberOfCommits += 1