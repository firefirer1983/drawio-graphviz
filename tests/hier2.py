import json
from transitions.extensions import HierarchicalGraphMachine
from transitions.extensions.nesting import NestedState, NestedEventData
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


class Model:
    def on_enter_b1(self, event: NestedEventData):
        pass

    def on_exit_b1(self, event: NestedEventData):
        pass

    def is_c1(self, event: NestedEventData):
        return True

    def not_c1(self, event: NestedEventData):
        return False

    def on_enter_b1_again(self, event: NestedEventData):
        pass

    def on_exit_b1_again(self, event: NestedEventData):
        pass

    def is_c1_again(self, event: NestedEventData):
        return True

    def not_c1_again(self, event: NestedEventData):
        return False


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
B1 = LabelNestedState(
    name=States.B1,
    on_enter=["on_enter_b1", "on_enter_b1_again"],
    on_exit=["on_exit_b1", "on_exit_b1_again"],
)
B = LabelNestedState(name=States.B)
B.add_substates([B1, C])


transitions = [
    Transition(source=str(States.Init), dest=NS(States.A, States.A1)),
    Transition(
        source=NS(States.A, States.A1),
        dest=NS(States.B, States.C, States.C1),
        conditions=["is_c1", "is_c1_agian"],
        unless=["not_c1", "not_c1_again"],
    ),
    Transition(
        source=NS(States.B, States.C, States.C1), dest=NS(States.B, States.C, States.C2)
    ),
    Transition(source=NS(States.B, States.C, States.C2), dest=NS(States.B, States.B1)),
]

machine = HierarchicalGraphMachine(
    states=[A, B],
    model=Model(),
    transitions=[asdict(t) for t in transitions],
    initial=States.Init,
    use_pygraphviz=False,
    ignore_invalid_triggers=True,
    show_conditions=True,
    show_state_attributes=True,
)


def draw2json(machine, filename: str):
    import pprint
    model = machine.model
    machine.show_conditions = False
    machine.show_state_attributes = False
    model.get_graph().draw(f"{filename}.json0", prog="dot")
    model.get_graph().draw(f"{filename}.png", prog="dot")
    machine.show_conditions = True
    machine.show_state_attributes = True
    model.get_graph().draw(f".{filename}.json0", prog="dot")
    with open(f"{filename}.json0", "r+") as t:
        with open(f".{filename}.json0", "r") as f:
            target = json.loads(t.read())
            label = json.loads(f.read())
            for dest, src in zip(target["objects"], label["objects"]):
                dest["label"] = src["label"]
            for dest, src in zip(target["edges"], label["edges"]):
                dest["label"] = src["label"]
        t.seek(0)
        t.truncate(0)
        t.write(json.dumps(target, indent=4))


def main():
    draw2json(machine, "hier2")


if __name__ == "__main__":
    main()
