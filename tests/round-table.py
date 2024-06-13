#! /usr/bin/env python

import io
import pprint
import json
import graphviz


dot = graphviz.Digraph('round-table', comment='The Round Table', format="json")
dot.node('A', 'King Arthur')
dot.node('B', 'Sir Bedevere the Wise')
dot.node('L', 'Sir Lancelot the Brave')
dot.edges(['AB', 'AL'])
dot.edge('B', 'L', constraint='false')


result = dot.pipe(encoding="utf-8")
pprint.pprint(json.loads(result))
with open(f"round-table.json", "w") as f:
    f.write(result)

