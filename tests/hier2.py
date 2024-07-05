from transitions.extensions import HierarchicalGraphMachine
from transitions.extensions.nesting import NestedState
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from argparse import ArgumentParser
from enum import Enum, EnumMeta

NestedState.separator = "."


def NS(*args):
    assert len(args) > 1, "缺少父状态"
    return NestedState.separator.join(str(arg) for arg in args)


@dataclass
class Transition:
    source: str
    dest: str
    conditions: Optional[List[str]] = field(default_factory=list)
    unless: Optional[List[str]] = field(default_factory=list)
    after: Optional[List[str]] = field(default_factory=list)
    before: Optional[List[str]] = field(default_factory=list)
    trigger: str = "next"


class StateEnum(Enum, metaclass=EnumMeta):
    def __repr__(self) -> str:
        return f"{self.name}"

    def __str__(self) -> str:
        return repr(self)


def LabelNestedState(
    name: StateEnum,
    on_enter=None,
    on_exit=None,
    ignore_invalid_triggers: bool = True,
    final: bool = False,
    initial: Optional[str] = None,
    on_final=None,
) -> NestedState:
    state = NestedState(
        name, on_enter, on_exit, ignore_invalid_triggers, final, initial, on_final
    )
    setattr(state, "label", name.value)
    return state


class States(StateEnum):
    Init = "初始化"
    A = "状态A"
    A1 = "状态A1"
    B = "状态B"
    B1 = "状态B1"
    C = "状态C"
    C1 = "状态C1"
    C2 = "状态C2"

Init = LabelNestedState(name=States.Init)
A1 = LabelNestedState(name=States.A1)
A = LabelNestedState(name=States.A)
A.add_substates([A1])
C1 = LabelNestedState(name=States.C1)
C2 = LabelNestedState(name=States.C2)
C = LabelNestedState(name=States.C)
C.add_substates([C1, C2])
B1 = LabelNestedState(name=States.B1)
B = LabelNestedState(name=States.B)
B.add_substates([B1, C])


transitions = [
    Transition(source=str(States.Init), dest=NS(States.A, States.A1)),
    Transition(source=NS(States.A, States.A1), dest=NS(States.B, States.C, States.C1)),
    Transition(
        source=NS(States.B, States.C, States.C1), dest=NS(States.B, States.C, States.C2)
    ),
    Transition(source=NS(States.B, States.C, States.C2), dest=NS(States.B, States.B1)),
]

machine = HierarchicalGraphMachine(
    states=[A, B],
    transitions=[asdict(t) for t in transitions],
    initial=States.Init,
    ignore_invalid_triggers=True,
)


def main():
    model = machine.model
    model.get_graph().draw("hier2.json0", prog="dot")
    model.get_graph().draw("hier2.png", prog="dot")

if __name__ == "__main__":
    main()
