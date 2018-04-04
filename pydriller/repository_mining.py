import logging

from pydriller.domain.commit import Commit
logging.getLogger(__name__).addHandler(logging.NullHandler())

from typing import List
from pydriller.scm.git_repository import GitRepository
from pydriller.domain.change_set import ChangeSet
from pydriller.scm.commit_visitor import CommitVisitor
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class RepositoryMining:
    def __init__(self, path_to_repo: str, visitor: CommitVisitor, single: str = None, since: datetime = None,
                 to: datetime = None, from_commit: str = None, to_commit: str = None, from_tag: str = None,
                 to_tag: str = None, reversed_order: bool = False, only_in_main_branch: bool = False,
                 only_in_branches: List[str]= None, only_modifications_with_file_types: List[str] = None,
                 only_no_merge: bool = False, num_threads: int = 1):
        """
        Init a repository mining.
        :param str path_to_repo: absolute path to the repository you have to mine
        :param CommitVisitor visitor: CommitVisitor that will visit all the specified commits
        :param str single: hash of a single commit to analyze
        :param datetime since: starting date
        :param datetime to: ending date
        :param str from_commit: starting commit (only if `since` is None)
        :param str to_commit: ending commit (only if `to` is None)
        :param str from_tag: starting the analysis from specified tag (only if `since` and `from_commit` are None)
        :param str to_tag: ending the analysis from specified tag (only if `to` and `to_commit` are None)
        :param bool reversed_order: whether the commits should be analyzed in reversed order
        :param bool only_in_main_branch: whether only commits in main branch should be analyzed
        :param List[str] only_in_branches: only commits in these branches will be analyzed
        :param List[str] only_modifications_with_file_types: only modifications with that file types will be analyzed
        :param bool only_no_merge: if True, merges will not be analyzed
        """
        self.git_repo = GitRepository(path_to_repo)
        self.visitor = visitor
        self.single = single
        self.since = since
        self.to = to
        self.reversed_order = reversed_order
        self.only_in_main_branch = only_in_main_branch
        self.only_in_branches = only_in_branches
        self.only_modifications_with_file_types = only_modifications_with_file_types
        self.only_no_merge = only_no_merge
        self.num_threads = num_threads

        self.__check_filters(from_commit, from_tag, since, single, to, to_commit, to_tag)

    def __check_filters(self, from_commit, from_tag, since, single, to, to_commit, to_tag):
        if single is not None:
            if since is not None or to is not None or from_commit is not None or \
                   to_commit is not None or from_tag is not None or to_tag is not None:
                raise Exception('You can not specify a single commit with other filters')

        if from_commit is not None:
            if since is not None:
                raise Exception('You can not specify both <since date> and <from commit>')
            self.since = self.git_repo.get_commit(from_commit).author_date

        if to_commit is not None:
            if to is not None:
                raise Exception('You can not specify both <to date> and <to commit>')
            self.to = self.git_repo.get_commit(to_commit).author_date

        if from_tag is not None:
            if since is not None or from_commit is not None:
                raise Exception('You can not specify <since date> or <from commit> when using <from tag>')
            self.since = self.git_repo.get_commit_from_tag(from_tag).author_date

        if to_tag is not None:
            if to is not None or to_commit is not None:
                raise Exception('You can not specify <to date> or <to commit> when using <to tag>')
            self.to = self.git_repo.get_commit_from_tag(to_tag).author_date

    def mine(self):
        """
        Starts the mining.
        """
        logging.info('Started the mining process')
        self.__process_repo()

    def __process_repo(self):
        logging.info('Git repository in {}'.format(self.git_repo.path))
        all_cs = self.__apply_filters_on_changesets(self.git_repo.get_change_sets())

        if not self.reversed_order:
            all_cs.reverse()

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            [executor.submit(self.__process_cs, cs) for cs in all_cs]

    def __process_cs(self, cs: ChangeSet):
        commit = self.git_repo.get_commit(cs.id)
        logging.info('Commit #{} in {} from {} with {} modifications'
                     .format(commit.hash, commit.author_date, commit.author.name, len(commit.modifications)))

        if self.__is_commit_filtered(commit):
            logging.info('Commit #{} filtered'.format(commit.hash))
            return

        self.visitor.process(self.git_repo, commit, None)

    def __is_commit_filtered(self, commit: Commit):
        if self.only_in_main_branch is True and commit.in_main_branch is False:
            logging.debug('Commit filtered for main branch')
            return True
        if self.only_in_branches is not None:
            logging.debug('Commit filtered for only in branches')
            if not self.__commit_branch_in_branches(commit):
                return True
        if self.only_modifications_with_file_types is not None:
            logging.debug('Commit filtered for modification types')
            if not self.__has_modification_with_file_type(commit):
                return True
        if self.only_no_merge is True and commit.merge is True:
            logging.debug('Commit filtered for no merge')
            return True
        return False

    def __commit_branch_in_branches(self, commit: Commit):
        for branch in commit.branches:
            if branch in self.only_in_branches:
                return True
        return False

    def __has_modification_with_file_type(self, commit):
        for mod in commit.modifications:
            if mod.filename.endswith(tuple(self.only_modifications_with_file_types)):
                return True
        return False

    def __apply_filters_on_changesets(self, all_cs: List[ChangeSet]) -> List[ChangeSet]:
        res = []

        if self.__all_filters_are_none():
            return all_cs

        for cs in all_cs:
            if self.single is not None and cs.id == self.single:
                return [cs]
            if self.since is None or self.since <= cs.date:
                if self.to is None or cs.date <= self.to:
                    res.append(cs)
                    continue
        return res

    def __all_filters_are_none(self):
        return self.single is None and self.since is None and self.to is None
