#! /usr/bin/env python

import io
import pprint
import json
import graphviz
import logging
from gvdraw.dpi import json_dapi72to96

logger = logging.getLogger(__name__)
dot = graphviz.Digraph(__name__, comment='The Round Table', format="json0")
dot.node_attr["shape"] = "box"
dot.node('A', 'King Arthur')
dot.node('B', 'Sir Bedevere the Wise')
dot.node('L', 'Sir Lancelot the Brave')
dot.edges(['AB', 'AL'])
dot.edge('B', 'L', constraint='false')


result = dot.pipe(encoding="utf-8")
logger.info(f"{result}")
result = json_dapi72to96(json.loads(result))
pprint.pprint(result)


dot = graphviz.Digraph(__name__, comment=__name__, format="png")
dot.node_attr["shape"] = "box"
dot.node('A', 'King Arthur')
dot.node('B', 'Sir Bedevere the Wise')
dot.node('L', 'Sir Lancelot the Brave')
dot.edges(['AB', 'AL'])
dot.edge('B', 'L', constraint='false')

dot.render(__name__)

