from typing import List, Optional, Union
from dataclasses import fields, dataclass
from jinja2 import Environment, FileSystemLoader

DEFAULT_NODE_SHAPE = "ellipse"
DEFAULT_CLUSTER_SHAPE = "rounded=0"


env = Environment(loader=FileSystemLoader("templates/"))
layout_factory = env.get_template("Layout.xml")
node_factory = env.get_template("Node.xml")
edge_factory = env.get_template("Edge.xml")
cluster_factory = env.get_template("Cluster.xml")


def todict(obj) -> dict:
    if not hasattr(obj, "__dataclass_fields__"):
        return obj
    result = dict()
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, (Node, Edge)):
            result[f.name] = value.cell_id
            continue
        result[f.name] = todict(value)
    return result


@dataclass
class Node:
    cell_id: str
    label: str
    x_pos: float
    y_pos: float
    width: float
    height: float
    parent: Optional[str] = None
    shape: str = DEFAULT_NODE_SHAPE

    def render(self) -> str:
        params = todict(self)
        params["x_pos"] = self.x_pos
        params["y_pos"] = self.y_pos
        params["width"] = self.width
        params["height"] = self.height
        return node_factory.render(**todict(self))


@dataclass
class Cluster:
    cell_id: str
    label: str
    x_pos: float
    y_pos: float
    width: float
    height: float
    parent: Optional[str] = None
    shape: str = DEFAULT_CLUSTER_SHAPE

    def render(self) -> str:
        params = todict(self)
        params["x_pos"] = self.x_pos
        params["y_pos"] = self.y_pos
        params["width"] = self.width
        params["height"] = self.height
        return cluster_factory.render(**todict(self))


@dataclass
class Edge:
    cell_id: str
    label: str
    source: str
    target: str
    edge_style: str = "orthogonalEdgeStyle"

    def render(self) -> str:
        params = todict(self)
        return edge_factory.render(**params)


@dataclass
class Layout:
    x_pos: float
    y_pos: float
    width: float
    height: float
    title: str
    nodes: List[Node]
    edges: List[Edge]

    def render(self) -> str:
        params = todict(self)
        params["x_pos"] = self.x_pos
        params["y_pos"] = self.y_pos
        params["width"] = self.width
        params["height"] = self.height
        params["nodes"] = "".join([node.render() for node in self.nodes])
        params["edges"] = "".join([edge.render() for edge in self.edges])
        return layout_factory.render(**params)
