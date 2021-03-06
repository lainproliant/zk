# --------------------------------------------------------------------
# zettel.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Thursday March 12, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------

import re
from panifex import sh, ShellReport
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional

# --------------------------------------------------------------------
ZETTEL_METADATA_PATTERN = r"^([\w-]+):(.*)$"  # e.g. "key: value"
ZETTEL_VALID_ID_PATTERN = r"^[\w-]+$"  # e.g. "20200314-note"
ZETTEL_REF_PATTERN = r"@([\\w-]+)"  # e.g. "@20200314-note"
EMPTY_LINE_PATTERN = r"^\s*$"


# --------------------------------------------------------------------
class ShellError(Exception):
    def __init__(self, msg, report: ShellReport):
        super().__init__(msg)
        self.report = report


# --------------------------------------------------------------------
class Zettel:
    def __init__(
        self,
        id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content: Optional[List[str]] = None,
    ):
        self._id = ""
        self.id = id
        self.title = title or self.id
        self.metadata = metadata or {}
        self.content = content or []

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Zettel) and self.id == other.id

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, id: str):
        if not re.match(ZETTEL_VALID_ID_PATTERN, id):
            raise ValueError(f"Invalid ID for zettel: '{id}'")
        self._id = id

    @classmethod
    def load_from_file(cls, location: Path) -> "Zettel":
        zettel_id = location.stem
        if not re.match(ZETTEL_VALID_ID_PATTERN, zettel_id):
            raise ValueError(f"Path stem is not a valid zettel id: {location.stem}")
        metadata: Dict[str, str] = {}
        content: List[str] = []
        with open(location, "r") as infile:
            for line in infile:
                match = re.match(ZETTEL_METADATA_PATTERN, line)
                if not match:
                    content.append(line)
                    break
                metadata[match.group(1).strip()] = match.group(2).strip()

            for line in infile:
                content.append(line)

        if "title" not in metadata:
            title = zettel_id
        else:
            title = metadata["title"]
            del metadata["title"]

        return Zettel(zettel_id, title, metadata, content)

    def save_to_file(self, location: Path):
        metadata = {"title": self.title, **self.metadata}

        with open(location, "w") as outfile:
            for key, value in metadata.items():
                print(f"{key}: {value}", file=outfile)
            for line in self.content:
                outfile.write(line)


# --------------------------------------------------------------------
@dataclass
class GraphNode:
    zettel: Zettel
    upstream: List["GraphNode"]
    downstream: List["GraphNode"]

    @property
    def neighbors(self) -> Set["GraphNode"]:
        return set([*self.upstream, *self.downstream])

    def __hash__(self) -> int:
        return hash(self.zettel.id)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, GraphNode) and self.zettel.id == other.zettel.id


# --------------------------------------------------------------------
class Zettelkasten:
    def __init__(self, location: Path, create=False, verbose=False):
        self.location = location
        self.branch = "master"
        if not self.location.exists():
            self.location.mkdir(parents=True)

    def sh(self, *args, **kwargs) -> ShellReport:
        return sh(*args, **{**kwargs, 'cwd': self.location}).no_echo().sync().report()

    def interactive_shell(self, cmd=None):
        return sh(cmd or '$SHELL', cwd=self.location).interactive().no_echo().sync().report()

    def path_for_zettel_id(self, zettel_id: str) -> Path:
        return self.location / f"{zettel_id}.md"

    def contains(self, zettel_id: str) -> bool:
        return self.path_for_zettel_id(zettel_id).exists()

    def load(self, zettel_id: str) -> Zettel:
        if not self.contains(zettel_id):
            raise ValueError(
                f"Zettel with ID '{zettel_id}' does not exist in the zettelkasten."
            )
        path = self.path_for_zettel_id(zettel_id)
        return Zettel.load_from_file(path)

    def save(self, zettel: Zettel):
        path = self.path_for_zettel_id(zettel.id)
        zettel.save_to_file(path)

    def has_changes(self) -> bool:
        report = self.sh('git status --porcelain')
        return len(list(report.output())) > 0

    def commit_changes(self):
        report = self.sh('git add .')
        if not report.succeeded():
            raise ShellError("Failed to add files to commit.", report)
        report = self.sh('git commit -m updates')
        if not report.succeeded():
            raise ShellError("Failed to commit.", report)

    def fetch_and_rebase(self):
        report = self.sh('git pull --rebase')
        if not report.succeeded():
            raise ShellError("Failed to fetch remote updates.", report)

    def push(self):
        report = self.sh('git push')
        if not report.succeeded():
            raise ShellError("Failed to push to remote origin.", report)

    def reidentify(self, zettel: Zettel, new_zettel_id: str) -> Zettel:
        # TODO implement
        pass

    def graph(self) -> Tuple[GraphNode, List[str]]:
        # TODO implement
        pass

    def add(self, zettel: Zettel):
        # TODO implement
        pass
