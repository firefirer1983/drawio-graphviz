#! /usr/bin/env python

import argparse
import logging
from functools import partial
from typing import List, Optional
import json
from dataclasses import dataclass, asdict, fields
from jinja2 import Environment, FileSystemLoader

DEFAULT_NODE_SHAPE = "elipse"

env = Environment(loader=FileSystemLoader("templates/"))
layout_factory = env.get_template("Layout.xml")
node_factory = env.get_template("Node.xml")
edge_factory = env.get_template("Edge.xml")

# POINT_TO_PIXEL = 1.33
POINT_TO_PIXEL = 1.0
DEFAULT_PADDING_SIZE = 4


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
        params["x_pos"] = self.x_pos * POINT_TO_PIXEL
        params["y_pos"] = self.y_pos * POINT_TO_PIXEL
        params["width"] = self.width * POINT_TO_PIXEL
        params["height"] = self.height * POINT_TO_PIXEL
        return node_factory.render(**todict(self))


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
        params["x_pos"] = self.x_pos * POINT_TO_PIXEL
        params["y_pos"] = self.y_pos * POINT_TO_PIXEL
        params["width"] = self.width * POINT_TO_PIXEL
        params["height"] = self.height * POINT_TO_PIXEL
        params["nodes"] = "".join([node.render() for node in self.nodes])
        params["edges"] = "".join([edge.render() for edge in self.edges])
        return layout_factory.render(**params)


def point2pixel(point: float) -> int:
    return int((point + DEFAULT_PADDING_SIZE) * POINT_TO_PIXEL)


def size2pixel(size: float) -> int:
    return int((size + 2 * DEFAULT_PADDING_SIZE) * POINT_TO_PIXEL)


# Dots Per Inch    
DEFAULT_DPI = 72


NODE_GVID_OFFSET = 2
DEFAULT_PARENT_NODE = "1"

def node_cell_id_offset(cell_id: str) -> str:
    return str(int(cell_id) + NODE_GVID_OFFSET)

def edge_cell_id_offset(offset, cell_id: str) -> str:
    return str(int(cell_id) + offset)

def unmarshal_xdot(xdot: dict) -> Layout:
    x_start, y_start, x_end, y_end = (float(x) for x in xdot["bb"].split(","))
    width, height = size2pixel(x_end - x_start), size2pixel(y_end - y_start)
    edges, nodes = [], {}
    for obj in xdot["objects"]:
        
        x_pos, y_pos = (point2pixel(float(x)) for x in obj["pos"].split(","))
        cell_id = obj["_gvid"]
        label = obj.get("label",obj["name"]) # if no label fallback to name
        node = Node(
            cell_id=str(cell_id),
            label=label,
            width=float(obj["width"]) * DEFAULT_DPI,
            height=float(obj["height"]) * DEFAULT_DPI,
            x_pos=x_pos,
            y_pos=y_pos,
        )
        nodes[cell_id] = node
        
    for edg in xdot.get("edges", []):
        head = nodes[edg["head"]]
        tail = nodes[edg["tail"]]
        label = edg.get("label", edg.get("name", ""))
        edges.append(
            Edge(
                cell_id=str(edg["_gvid"]),
                source=tail.cell_id,
                target=head.cell_id,
                label=label,
            )
        )
    node_offset = node_cell_id_offset
    for node in nodes.values():
        node.cell_id = node_offset(node.cell_id)
        if node.parent is None:
            node.parent = DEFAULT_PARENT_NODE
            
    max_node_id = max([int(n.cell_id) for n in nodes.values()])
    edge_offset =  partial(edge_cell_id_offset, max_node_id + 1)
    
    for edg in edges:
        edg.cell_id = edge_offset(edg.cell_id)
        edg.source = node_offset(edg.source)
        edg.target = node_offset(edg.target)

    return Layout(
        x_pos=0,
        y_pos=0,
        width=width,
        height=height,
        title="",
        nodes=list(nodes.values()),
        edges=edges,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src_json")
    args = parser.parse_args()
    filebasename, *_ = args.src_json.split(".json")
    logging.info(f"{args.src_json} => {filebasename}.xml")
    with open(f"{args.src_json}", "r") as f:
        xdot = json.loads(f.read())
        layout = unmarshal_xdot(xdot)
        logging.info(f"{layout.render()}")
        with open(f"{filebasename}.xml", "w") as toxml:
            toxml.write(layout.render())


if __name__ == "__main__":
    main()
