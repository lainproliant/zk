# --------------------------------------------------------------------
# main.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Thursday March 12, 2020
#
# Distributed under terms of the MIT license.
# --------------------------------------------------------------------

import os
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import check_call
from typing import Dict, List, Optional, Type

from ansilog import fg, getLogger

from .zettel import Zettel, Zettelkasten, ShellError

# --------------------------------------------------------------------
DEFAULT_ZK_PATH = Path.home() / "zk"
DEFAULT_ZETTEL = "index"

# --------------------------------------------------------------------
log = getLogger("zk")


# --------------------------------------------------------------------
error = log.error
info = log.info


# --------------------------------------------------------------------
class UnknownActionError(Exception):
    def __init__(self, action):
        self.action = action


# --------------------------------------------------------------------
@dataclass
class ActionMap:
    _map: Dict[str, Type["Action"]] = field(default_factory=dict)
    default_action: Optional[Type["Action"]] = None

    def actions(self) -> List[str]:
        return list(sorted(self._map.keys()))

    def default(self, name: Optional[str] = None):
        def define_impl(f):
            self.__call__(f)
            self.default_action = f

        return define_impl

    def __call__(self, name: Optional[str] = None):
        def define_impl(f):
            f.name = name or f.__name__
            self._map[f.name] = f
            return f

        return define_impl

    def __getitem__(self, name: str) -> Type["Action"]:
        if name not in self._map:
            raise UnknownActionError(name)
        return self._map[name]


# --------------------------------------------------------------------
actions = ActionMap()


# --------------------------------------------------------------------
class Action(Namespace):
    name = __name__

    def __init__(self):
        self.action: Optional[str] = None
        self.show_help = False

    @classmethod
    def get_parser(cls) -> ArgumentParser:
        parser = ArgumentParser(
            description="Manage your notes using a zettelkasten.", add_help=False
        )
        parser.add_argument("action", metavar="ACTION", nargs="?")
        parser.add_argument("-h", "--help", dest="show_help", action="store_true")
        return parser

    def resolve(self) -> "Action":
        self.get_parser().parse_known_args(namespace=self)
        action = actions[self.action or DefaultAction.name]()
        return action.parse_args()

    def parse_args(self) -> "Action":
        self.get_parser().parse_args(namespace=self)
        self.setup()
        return self

    def setup(self):
        if self.show_help:
            self.help()
            sys.exit(0)

    @classmethod
    def help(cls):
        info(fg.bright.cyan("# Available commands:"))
        for key in sorted(actions.actions()):
            if key.startswith("_"):
                continue
            action_class = actions[key]
            info(
                f"- {fg.bright.magenta(key)}: {(action_class.__doc__ or '???').strip()}"
            )

    def __call__(self) -> int:
        raise NotImplementedError()


# --------------------------------------------------------------------
@actions("_default")
class DefaultAction(Action):
    def __call__(self):
        self.help()


# --------------------------------------------------------------------
class ZettelkastenAction(Action):
    def __init__(self):
        super().__init__()
        self._zk: Optional[Zettelkasten] = None
        self._zk_path = DEFAULT_ZK_PATH

    @property
    def zk(self) -> Zettelkasten:
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
        parser.add_argument("_zettel_id", metavar="ID", nargs="?")
        return parser

    def setup(self):
        super().setup()

        if self.zk.contains(self.zettel_id):
            self.zettel = self.zk.load(self.zettel_id)
        else:
            self.zettel = Zettel(self.zettel_id)


# --------------------------------------------------------------------
@actions("sh")
class ShellAction(ZettelkastenAction):
    """Drop into an interactive shell within the zettelkasten."""

    def __init__(self):
        super().__init__()
        self._cmd = None

    def __call__(self) -> int:
        self.zk.interactive_shell(self._cmd)
        return 0

    @classmethod
    def get_parser(cls) -> ArgumentParser:
        parser = super().get_parser()
        parser.add_argument("-c", type=str, dest="_cmd")
        return parser

# --------------------------------------------------------------------
@actions("sync")
class SyncAction(ZettelkastenAction):
    """Commit any changes then merge any changes from the remote."""

    def __call__(self) -> int:
        if self.zk.has_changes():
            self.zk.commit_changes()
        self.zk.fetch_and_rebase()
        self.zk.push()

        return 0


# --------------------------------------------------------------------
@actions("edit")
class EditZettel(ZettelAction):
    """Edit the contents of a zettel.  Creates it if it doesn't exist yet."""

    def __call__(self) -> int:
        editor = os.environ.get("EDITOR", "vim")
        path = self.zk.path_for_zettel_id(self.zettel.id)
        if not path.exists():
            self.zk.save(self.zettel)
        check_call([editor, path])
        return 0


# --------------------------------------------------------------------
@actions("_prepare")
class PrepareZettelFile(ZettelAction):
    def __call__(self) -> int:
        if not self.zk.contains(self.zettel.id):
            self.zk.save(self.zettel)
        print(str(self.zk.path_for_zettel_id(self.zettel.id).absolute()))
        return 0


# --------------------------------------------------------------------
def main():
    try:
        action = Action().resolve()

    except UnknownActionError as e:
        error("Unknown action: %s" % e.action)
        DefaultAction.help()
        sys.exit(1)

    try:
        sys.exit(action())

    except ShellError as e:
        error("A subcommand failed: `%s`" % e.report.cmd)
        e.report.log_output(log=log)
        sys.exit(1)



# --------------------------------------------------------------------
if __name__ == "__main__":
    main()
