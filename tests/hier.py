from transitions.extensions import HierarchicalGraphMachine
from transitions.extensions.nesting import NestedState
from argparse import ArgumentParser

NestedState.separator = "."


states = [
    {"name": 'A', "children": [{"name": "A1"}]},
    {"name": 'B', "children": [{"name": "B1"}, {"name": "C", "children": [{"name": "C1"}, {"name": "C2"}]}]}    
]
transitions = [
  ['next', 'A.A1', 'B.C.C1'],
  ['next', 'B.C.C1', 'B.C.C2'],
  ['next', 'B.C.C2', 'B.B1'],
]

machine = HierarchicalGraphMachine(states=states, transitions=transitions, initial='A.A1', ignore_invalid_triggers=True)


def main():
    parser = ArgumentParser()
    parser.add_argument("format")
    args = parser.parse_args()
    model = machine.model
    model.get_graph().draw("hier", prog='dot', format=args.format)


if __name__ == "__main__":
    main()
