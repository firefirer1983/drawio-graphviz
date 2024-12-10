#! /usr/bin/env python

import io
import pprint
import json
import graphviz
from gvdraw.dpi import json_dapi72to96

dot = graphviz.Digraph('single-node', comment='The Single Node', format="json0")
# dot.graph_attr["dpi"] = "96"
dot.node_attr["shape"] = "box"
dot.node('A', 'Node', shape='box')
# dot.node('B', 'Node', shape='box')
# dot.edge('A', 'B')

result = dot.pipe(encoding="utf-8")
result = json_dapi72to96(json.loads(result))
pprint.pprint(result)

dot = graphviz.Digraph('single-node', comment='The Single Node', format="png")
dot.node('A', 'Node', shape='box')


# dot.node('B', 'Node', shape='box')
# dot.edge('A', 'B')

dot.render("node-edge")
    
