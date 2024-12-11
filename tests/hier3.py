from transitions.extensions import HierarchicalGraphMachine

states = [
    "standing",
    "walking",
    {"name": "caffeinated", "children": ["dithering", "running"]},
]
transitions = [
    ["walk", "standing", "walking"],
    ["stop", "walking", "standing"],
    ["drink", "*", "caffeinated"],
    ["walk", ["caffeinated", "caffeinated_dithering"], "caffeinated_running"],
    ["relax", "caffeinated", "standing"],
]

machine = HierarchicalGraphMachine(
    states=states,
    transitions=transitions,
    use_pygraphviz=False,
    ignore_invalid_triggers=True,
    show_conditions=True,
    show_state_attributes=True,
    initial="standing",
)

graph = machine.get_graph()
graph.attr(rankdir="TB")

graph.node_attr["style"] = ""

graph.draw(filename="hier.json", format="json0")
graph.draw(filename="hier.png", format="png")
