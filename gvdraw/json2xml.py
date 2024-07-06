#! /usr/bin/env python

import argparse
import logging
import json
from gvdraw.dpi import size_padding, position_paddiing, inch2pixel

import logging
from typing import List, Optional, Set, Union, Dict, Tuple
from dataclasses import InitVar, field, fields, dataclass, asdict
from jinja2 import Environment, FileSystemLoader
from gvdraw.dpi import size_padding, position_paddiing, inch2pixel


def strip_label(label: str):
    return label.strip().strip(NEWLINE).strip()


NODE_GVID_OFFSET = 2

STATE_SEP = "."
DEFAULT_NODE_SHAPE = "rounded=0"
DEFAULT_CLUSTER_SHAPE = "rounded=0"
DEFAULT_PARENT_NODE = "1"
NODE_PREFIX = "nodes-"
EDGE_PREFIX = "edges-"
NEWLINE = "\\l"
ENTER_TAG = "- enter:"
EXIT_TAG = "- exit:"
ON_CONNECTOR = "+"


def node_cell_id_offset(cell_id: str) -> str:
    return str(int(cell_id) + NODE_GVID_OFFSET)


def edge_cell_id_offset(offset, cell_id: str) -> str:
    return str(int(cell_id) + offset)


env = Environment(loader=FileSystemLoader("templates/"))
layout_factory = env.get_template("Layout.xml")
node_factory = env.get_template("Node.xml")
edge_factory = env.get_template("Edge.xml")
cluster_factory = env.get_template("Cluster.xml")


@dataclass
class StateLabel:
    string: InitVar[str]
    label: str = field(init=False)
    on_enter: List[str] = field(init=False)
    on_exit: List[str] = field(init=False)

    def __post_init__(self, string: str):
        self.label = strip_label(string)
        self.on_enter, self.on_exit = list(), list()
        on_enter_string = on_exit_string = ""
        if EXIT_TAG in self.label:
            self.label, on_exit_string = self.label.split(EXIT_TAG)
            on_exit_string = strip_label(on_exit_string)
            self.label = strip_label(self.label)
            self.on_exit = [strip_label(f) for f in on_exit_string.split(ON_CONNECTOR) if f]

        if ENTER_TAG in self.label:
            self.label, on_enter_string = self.label.split(ENTER_TAG)
            on_enter_string = strip_label(on_enter_string)
            self.label = strip_label(self.label)
            self.on_enter = [
                strip_label(f) for f in on_enter_string.split(ON_CONNECTOR) if f
            ]

    def parse(self) -> Tuple[str, List[str], List[str]]:
        return self.label, self.on_enter.copy(), self.on_exit.copy()


@dataclass
class TransitionLabel:
    string: InitVar[str]
    label: str = field(init=False)
    conditions: List[str] = field(init=False)
    unless: List[str] = field(init=False)

    def __post_init__(self, string: str):
        if " " not in string:
            self.label, self.conditions, self.unless = string, list(), list()
            return
        self.label, left = string.split(" ", 1)
        self.conditions, self.unless = list(), list()
        left = left.strip().strip("[").strip("]").strip()
        parts = [part.strip() for part in left.split("&")]
        for part in parts:
            if "!" in part:
                self.unless.append(part.strip("!"))
                continue
            self.conditions.append(part.strip("!"))

    def parse(self) -> Tuple[str, List[str], List[str]]:
        return self.label, self.conditions.copy(), self.unless.copy()


def is_cluster(name: str):
    return name and name.startswith("cluster_")


def is_cluster_root(name: str):
    return is_cluster(name) and name.endswith("_root")


def sanitize_statename(name: str) -> str:
    name = name.strip().strip(NEWLINE)
    _name = name
    logging.info(f"name: {name}")
    if is_cluster_root(name):
        name, _ = name.split("_root")
    if is_cluster(name):
        _, name = name.split("cluster_")
    *_, state = name.split(STATE_SEP)
    # logging.info(f"statename: {_name} => {state}")
    return state


@dataclass
class Node:
    xdot: InitVar[dict]
    cell_id: str = field(init=False)
    name: str = field(init=False)
    label: str = field(init=False)
    x_pos: float = field(init=False)
    y_pos: float = field(init=False)
    height: float = field(init=False)
    width: float = field(init=False)
    shape: str = field(init=False)
    parent: str = DEFAULT_PARENT_NODE
    on_enter: List[str] = field(init=False)
    on_exit: List[str] = field(init=False)

    def __post_init__(self, xdot):
        x_, y_ = xdot["pos"].split(",")
        self.x_pos = position_paddiing(x_)
        self.y_pos = position_paddiing(y_)
        self.cell_id = NODE_PREFIX + str(xdot["_gvid"])
        self.width = inch2pixel(xdot["width"])
        self.height = inch2pixel(xdot["height"])
        self.name = sanitize_statename(xdot["name"])
        self.label, self.on_enter, self.on_exit = StateLabel(xdot["label"]).parse()
        self.shape = (
            DEFAULT_NODE_SHAPE
            if xdot.get("shape", "retangle") == "rectangle"
            else xdot.get("shape")
        )

    def vflip(self, vcanvas: float):
        self.y_pos = vcanvas - (self.y_pos + self.height)
        return self

    def render(self) -> str:
        attrs = asdict(self)
        return node_factory.render(**attrs)

    @property
    def is_cluster(self) -> bool:
        return False

    @property
    def is_cluster_root(self) -> bool:
        return False

    @property
    def is_point(self):
        return self.shape == "point"


@dataclass
class Cluster(Node):
    shape: str = DEFAULT_CLUSTER_SHAPE

    def __post_init__(self, xdot):
        x_start, y_start, x_end, y_end = (float(x) for x in xdot["bb"].split(","))
        self.width, self.height = (
            size_padding(x_end - x_start),
            size_padding(y_end - y_start),
        )
        self.x_pos = position_paddiing(x_start)
        self.y_pos = position_paddiing(y_start)
        self.cell_id = NODE_PREFIX + str(xdot["_gvid"])
        self.name = sanitize_statename(xdot["name"])
        self.label, self.on_enter, self.on_exit = StateLabel(xdot["label"]).parse()

    def vflip(self, vcanvas: float):
        self.y_pos = vcanvas - (self.y_pos + self.height)
        return self

    @property
    def is_cluster(self) -> bool:
        return True


@dataclass
class Root(Cluster):
    def __post_init__(self, xdot):
        pass

    @property
    def is_cluster_root(self) -> bool:
        return True


def obj2node(obj: dict) -> Node:
    if is_cluster_root(obj["name"]):
        logging.info(f"{obj['_gvid']} : Root")
        return Root(obj)
    elif is_cluster(obj["name"]):
        logging.info(f"{obj['_gvid']} : Cluster")
        return Cluster(obj)
    else:
        logging.info(f"{obj['_gvid']} : Node")
        return Node(obj)


@dataclass
class Edge:
    xdot: InitVar[dict]
    cell_id: str = field(init=False)
    label: str = field(init=False)
    source: str = field(init=False)
    target: str = field(init=False)
    conditions: List[str] = field(init=False)
    unless: List[str] = field(init=False)
    edge_style: str = "orthogonalEdgeStyle"

    def __post_init__(self, xdot):
        self.cell_id = EDGE_PREFIX + str(xdot["_gvid"])
        self.source = NODE_PREFIX + str(xdot["tail"])
        self.target = NODE_PREFIX + str(xdot["head"])
        self.label, self.conditions, self.unless = TransitionLabel(
            xdot["label"]
        ).parse()

    def render(self) -> str:
        return edge_factory.render(**asdict(self))


@dataclass
class Layout:
    xdot: InitVar[dict]
    x_pos: float = field(init=False)
    y_pos: float = field(init=False)
    width: float = field(init=False)
    height: float = field(init=False)
    title: str = field(init=False)
    nodes: List[Node] = field(init=False)
    edges: List[Edge] = field(init=False)

    def __post_init__(self, xdot):
        self.nodes, self.edges = list(), list()
        self.title = xdot["name"]
        x_start, y_start, x_end, y_end = (float(x) for x in xdot["bb"].split(","))
        self.width, self.height = (
            size_padding(x_end - x_start),
            size_padding(y_end - y_start),
        )
        self.x_pos, self.y_pos = 0, 0

        self.nodes = [
            # Cluster(
            #     {
            #         "_gvid": "layout",
            #         "name": "layout",
            #         "bb": xdot["bb"],
            #         "label": "layout",
            #         "shape": "rectangle",
            #     }
            # )
        ]

        for obj in xdot["objects"]:
            node = obj2node(obj)
            if node.is_cluster_root or node.is_point:
                continue
            self.nodes.append(node.vflip(self.height))

        for edg in xdot["edges"]:
            edge = Edge(edg)
            self.edges.append(edge)

    def render(self) -> str:
        params = dict()
        params["x_pos"] = self.x_pos
        params["y_pos"] = self.y_pos
        params["width"] = self.width
        params["height"] = self.height
        params["nodes"] = "".join([node.render() for node in self.nodes])
        params["edges"] = "".join([edge.render() for edge in self.edges])
        return layout_factory.render(**params)


@dataclass
class State:
    gvid: int
    payload: dict
    substates: List["State"] = field(default_factory=list)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    args = parser.parse_args()
    filebasename, *_ = args.src.split(".json0")
    logging.info(f"{args.src} => {filebasename}.xml")
    with open(f"{args.src}", "r") as f:
        xdot = json.loads(f.read())
        layout = Layout(xdot)
        logging.info(f"{layout.render()}")
        with open(f"{filebasename}.xml", "w") as toxml:
            toxml.write(layout.render())


if __name__ == "__main__":
    main()
