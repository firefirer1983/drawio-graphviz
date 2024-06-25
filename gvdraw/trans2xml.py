from transitions.extensions import HierarchicalGraphMachine
from argparse import ArgumentParser
states = ['standing', 'walking', {'name': 'caffeinated', 'children':['dithering', 'running']}]
transitions = [
  ['walk', 'standing', 'walking'],
  ['stop', 'walking', 'standing'],
  ['drink', '*', 'caffeinated'],
  ['walk', ['caffeinated', 'caffeinated_dithering'], 'caffeinated_running'],
  ['relax', 'caffeinated', 'standing']
]

machine = HierarchicalGraphMachine(states=states, transitions=transitions, initial='standing', ignore_invalid_triggers=True)


def main():
    parser = ArgumentParser()
    parser.add_argument("format")
    args = parser.parse_args()
    model = machine.model
    model.get_graph().draw("hier", prog='dot', format=args.format)


if __name__ == "__main__":
    main()
