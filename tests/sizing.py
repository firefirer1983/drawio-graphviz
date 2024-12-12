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
A = LabelNestedState(name=States.A)


transitions = [
    Transition(source=str(States.Init), dest=str(States.A)),
]

machine = HierarchicalGraphMachine(
    states=[A],
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
    machine.show_conditions = True
    machine.show_state_attributes = True

    graph = model.get_graph()
    graph.attr(rankdir="BT")
    graph.node_attr["shape"] = "box"
    breakpoint()
    graph.draw(f"{filename}.json0", prog="dot")
    graph.draw(f"{filename}.png", prog="dot")
    


def main():
    draw2json(machine, "sizing")


if __name__ == "__main__":
    main()
