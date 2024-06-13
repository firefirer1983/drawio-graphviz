#! /usr/bin/env python

import io
import pprint
import json
import graphviz


dot = graphviz.Digraph('single-node', comment='The Single Node', format="json")
dot.node('A', 'Node', shape='box')
dot.node('B', 'Node', shape='box')
dot.edge('A', 'B')

result = dot.pipe(encoding="utf-8")
pprint.pprint(json.loads(result))
with open(f"single-node.json", "w") as f:
    f.write(result)

dot = graphviz.Digraph('single-node', comment='The Single Node', format="png")
dot.node('A', 'Node', shape='box')
dot.node('B', 'Node', shape='box')
dot.edge('A', 'B')

dot.render("node-edge")
    
