import logging
from typing import List, Optional, Union, Dict
from dataclasses import field, fields, dataclass
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
class TreeNode:
    gvid: int
    name: str
    data: dict
    
    children: List["TreeNode"] = field(default_factory=list)
    subgraphs: List[int] = field(default_factory=list)
    nodes: List[int] = field(default_factory=list)

    @property
    def is_cluster(self) -> bool:
        return self.name.startswith("cluster_") and not self.name.endswith("_root")

    @property
    def is_cluster_root(self) -> bool:
        return self.name.startswith("cluster_") and self.name.endswith("_root")

    @property
    def label(self):
        if self.is_cluster:
            _, name, *_ = self.name.split("_")
            return name
        return self.name


def get_leaves(node: TreeNode) -> List[TreeNode]:
    for graph in node.subgraphs:
        pass
    return []
        

def parse_subtree(node: TreeNode, nmap: Dict[int, TreeNode]) -> List[TreeNode]:
    if node.subgraphs:
        subgraphs = [parse_subtree(nmap[gvid], nmap) for gvid in node.subgraphs]
    return subgraphs +  [nmap[gvid] for gvid in node.nodes]


def parse_tree_from(xdot: dict):
    nodes = [
        TreeNode(
            gvid=obj["_gvid"],
            name=obj["name"],
            data=obj,
            subgraphs=obj["subgraphs"],
            nodes=obj["nodes"],
        )
        for obj in xdot["objects"]
    ]
    node_map = {n.gvid: n for n in nodes}
    for node in nodes:
        node.children = parse_subtree(node, node_map)


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


@dataclass
class State:
    gvid: int
    payload: dict
    substates: List["State"] = field(default_factory=list)
