#! /usr/bin/env python

import argparse
import logging
from functools import partial
import json
from gvdraw.base import Node, Layout, Edge, Cluster
from gvdraw.dpi import size_padding, position_paddiing, inch2pixel


NODE_GVID_OFFSET = 2
DEFAULT_PARENT_NODE = "1"


def node_cell_id_offset(cell_id: str) -> str:
    return str(int(cell_id) + NODE_GVID_OFFSET)


def edge_cell_id_offset(offset, cell_id: str) -> str:
    return str(int(cell_id) + offset)


def unmarshal_xdot(xdot: dict) -> Layout:
    x_start, y_start, x_end, y_end = (float(x) for x in xdot["bb"].split(","))
    width, height = size_padding(x_end - x_start), size_padding(y_end - y_start)
    edges, nodes = [], {}
    for obj in xdot["objects"]:
        x_, y_ = obj["pos"].split(",")
        x_pos = position_paddiing(x_)
        # Y方向取反
        y_pos = height - position_paddiing(y_)
        cell_id = obj["_gvid"]
        label = obj.get("label", obj["name"])  # if no label fallback to name
        node = Node(
            cell_id=str(cell_id),
            label=label,
            width=inch2pixel(obj["width"]),
            height=inch2pixel(obj["height"]),
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
    edge_offset = partial(edge_cell_id_offset, max_node_id + 1)

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
    parser.add_argument("src")
    args = parser.parse_args()
    filebasename, *_ = args.src.split(".json")
    logging.info(f"{args.src} => {filebasename}.xml")
    with open(f"{args.src}", "r") as f:
        xdot = json.loads(f.read())
        layout = unmarshal_xdot(xdot)
        logging.info(f"{layout.render()}")
        with open(f"{filebasename}.xml", "w") as toxml:
            toxml.write(layout.render())


if __name__ == "__main__":
    main()
