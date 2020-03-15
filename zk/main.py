# --------------------------------------------------------------------
# main.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Thursday March 12, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------

import sys
import os
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import check_call
from typing import Dict, List, Optional, Type

from .zettel import Zettel, Zettelkasten

# --------------------------------------------------------------------
DEFAULT_ZK_PATH = Path.home() / "zettelkasten"
DEFAULT_ZETTEL = "index"

# --------------------------------------------------------------------
@dataclass
class ActionMap:
    _map: Dict[str, Type["Action"]] = field(default_factory=dict)

    def actions(self) -> List[str]:
        return list(sorted(self._map.keys()))

    def __call__(self, name: Optional[str] = None):
        def define_impl(f):
            self._map[name or f.__name__] = f
            return f

        return define_impl

    def __getitem__(self, name: str) -> Type["Action"]:
        if name not in self._map:
            raise ValueError('Unknown action: %s' % name)
        return self._map[name]


# --------------------------------------------------------------------
actions = ActionMap()


# --------------------------------------------------------------------
class Action(Namespace):
    def __init__(self):
        self.action = "edit"

    @classmethod
    def get_parser(cls) -> ArgumentParser:
        parser = ArgumentParser(description="Manage your notes using a zettelkasten.")
        parser.add_argument('action', metavar="ACTION")
        return parser

    def resolve(self) -> "Action":
        self.get_parser().parse_known_args(namespace=self)
        action = actions[self.action]()
        return action.parse_args()

    def parse_args(self) -> "Action":
        self.get_parser().parse_args(namespace=self)
        self.setup()
        return self

    def setup(self):
        pass

    def __call__(self) -> int:
        raise NotImplementedError()


# --------------------------------------------------------------------
class ZettelkastenAction(Action):
    def __init__(self):
        super().__init__()
        self._zk: Optional[Zettelkasten] = None
        self._zk_path = DEFAULT_ZK_PATH

    @property
    def zettelkasten(self) -> Zettelkasten:
        if self._zk is None:
            raise ValueError("Zettelkasten was not loaded.")
        return self._zk

    @classmethod
    def get_parser(cls) -> ArgumentParser:
        parser = super().get_parser()
        parser.add_argument("-Z", type=Path, dest="_zk_path")
        return parser

    def setup(self):
        super().setup()
        self._zk = Zettelkasten(self._zk_path)


# --------------------------------------------------------------------
class ZettelAction(ZettelkastenAction):
    def __init__(self):
        super().__init__()
        self._zettel: Optional[Zettel] = None
        self._zettel_id: Optional[str] = None

    @property
    def zettel_id(self) -> str:
        if self._zettel_id is None:
            self._zettel_id = DEFAULT_ZETTEL
        return self._zettel_id

    @property
    def zettel(self) -> Zettel:
        if self._zettel is None:
            raise ValueError("Zettel was not loaded.")
        return self._zettel

    @zettel.setter
    def zettel(self, ztl: Zettel):
        self._zettel = ztl

    @classmethod
    def get_parser(cls) -> ArgumentParser:
        parser = super().get_parser()
        parser.add_argument('_zettel_id', metavar="ID", nargs="?")
        return parser

    def setup(self):
        super().setup()

        if self.zettelkasten.contains(self.zettel_id):
            self.zettel = self.zettelkasten.load(self.zettel_id)
        else:
            self.zettel = Zettel(self.zettel_id)


# --------------------------------------------------------------------
@actions("edit")
class EditZettel(ZettelAction):
    def __call__(self) -> int:
        editor = os.environ.get("EDITOR", "vim")
        path = self.zettelkasten.path_for_zettel_id(self.zettel.id)
        if not path.exists():
            self.zettelkasten.save(self.zettel)
        check_call([editor, path])
        return 0


# --------------------------------------------------------------------
@actions("prepare")
class PrepareZettelFile(ZettelAction):
    def __call__(self) -> int:
        if not self.zettelkasten.contains(self.zettel.id):
            self.zettelkasten.save(self.zettel)
        print(str(self.zettelkasten.path_for_zettel_id(self.zettel.id).absolute()))
        return 0


# --------------------------------------------------------------------
def main():
    action = Action().resolve()
    sys.exit(action())


# --------------------------------------------------------------------
if __name__ == "__main__":
    main()
