from collections import deque
import logging
import ast
from jinja2 import Environment, FileSystemLoader
from typing import List
from dataclasses import dataclass, field, InitVar
from argparse import ArgumentParser
from xml.etree.ElementTree import fromstring, Element

env = Environment(loader=FileSystemLoader("templates/"))
state_factory = env.get_template("State.tmpl")
state_add_children_factory = env.get_template("StateAddChildren.tmpl")

transition_factory = env.get_template("Transition.tmpl")


def is_edge(obj: Element) -> bool:
    children = list(obj)
    if not children:
        return False
    return bool(children[0].get("edge", False))


def is_vertex(obj: Element) -> bool:
    children = list(obj)
    if not children:
        return False
    return bool(children[0].get("vertex", False))


@dataclass
class XMLNode:
    xdata: InitVar[Element]
    label: str = field(init=False)
    name: str = field(init=False)
    on_enter: List[str] = field(init=False)
    on_exit: List[str] = field(init=False)
    x_pos: int = field(init=False)
    y_pos: int = field(init=False)
    width: int = field(init=False)
    height: int = field(init=False)
    children: List["XMLNode"] = field(init=False)

    def __post_init__(self, xdata: Element):
        mxcell = list(xdata)[0]
        mxgeo = list(mxcell)[0]
        self.label = xdata.get("label", "")
        self.name = xdata.get("name", "")

        self.on_enter = ast.literal_eval(xdata.get("on_enter", "[]"))
        self.on_exit = ast.literal_eval(xdata.get("on_exit", "[]"))
        self.x_pos = int(mxgeo.get("x", 0))
        self.y_pos = int(mxgeo.get("y", 0))
        self.height = int(mxgeo.get("height", 0))
        self.width = int(mxgeo.get("width", 0))
        self.children = list()

    def add_child(self, child: "XMLNode"):
        self.children.append(child)

    def __contains__(self, node: "XMLNode") -> bool:
        if self.x_pos > node.x_pos:
            return False
        if self.y_pos > node.y_pos:
            return False
        if self.x_pos + self.width < node.x_pos + node.width:
            return False
        if self.y_pos + self.height < node.y_pos + node.height:
            return False
        logging.info(
            f"{node.label}@{node.pos}[{node.size}] in {self.label}@{self.pos}[{self.size}]"
        )
        return True

    @property
    def pos(self):
        return (self.x_pos, self.y_pos)

    @property
    def size(self):
        return self.width * self.height

    @property
    def substates(self) -> List[str]:
        return [c.name for c in self.children]

    def __lt__(self, node: "XMLNode") -> bool:
        return self.size < node.size

    def __gt__(self, node: "XMLNode") -> bool:
        return self.size > node.size

    def __repr__(self) -> str:
        string = ""
        for child in self.children:
            string += f" {child.label}"
        string = f"XMLNode(label={self.label}, name={self.name}, pos={self.pos}, size={self.size} children=[{string}])"
        return string

    def __str__(self) -> str:
        return repr(self)



@dataclass
class XMLEdge:
    xdata: InitVar[Element]
    label: str = field(init=False)
    name: str = field(init=False)
    source: str = field(init=False)
    target: str = field(init=False)
    conditions: List[str] = field(init=False)

    def __post_init__(self, xdata: Element):
        self.label = ""


def unmarshal_states(nodes: List[XMLNode]) -> str:
    template = env.get_template("State.tmpl")
    return template.render(states=nodes)


@dataclass
class XMLLayout:
    xdata: InitVar[str]
    tree: List[XMLNode] = field(init=False)
    edges: List[XMLEdge] = field(init=False)
    nodes: List[XMLNode] = field(init=False)

    def __post_init__(self, xdata: str):
        root = fromstring(xdata)
        self.edges, self.nodes, self.tree = list(), list(), list()

        nodes = list()
        for obj in root.iter("object"):
            if is_vertex(obj):
                nodes.append(XMLNode(obj))
                continue
            if is_edge(obj):
                self.edges.append(XMLEdge(obj))
                continue
            logging.warning(f"Unknown type element: {obj}")

        # order by size => nodes
        nodes = sorted(nodes, key=lambda x: x)
        while nodes:
            n = nodes.pop(0)
            for p in nodes:
                if n not in p:
                    continue
                logging.info(f"{n.label} => {p.label}")
                p.add_child(n)
                break
            else:
                self.tree.append(n)

        # BFS => self.nodes
        lifo = deque(self.tree)
        while lifo:
            state = lifo.popleft()
            self.nodes.append(state)
            for child in state.children:
                lifo.append(child)

    def unmarshal(self):
        return unmarshal_states(self.nodes)


def main():
    parser = ArgumentParser()
    parser.add_argument("src", type=str)
    args = parser.parse_args()
    with open(f"{args.src}", "r") as f:
        layout = XMLLayout(f.read())
        logging.info(f"\n{layout.unmarshal()}")


if __name__ == "__main__":
    main()
