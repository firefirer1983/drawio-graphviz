import logging
from pathlib import Path
import importlib
from transitions.extensions import HierarchicalGraphMachine
from dataclasses import dataclass, asdict, fields
from typing import List, Optional, Union
from functools import partial

from jinja2 import Environment, FileSystemLoader

from argparse import ArgumentParser


def main():
    parser = ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("format")
    args = parser.parse_args()
    filebasename, *_ = args.src.split(".py")
    mpath = Path(filebasename)
    logging.info(f"{args.src} => {filebasename}.xml")
    module = importlib.import_module(".".join(mpath.parts))
    module_name = mpath.parts[-1]
    for key in dir(module):
        if key.startswith("__"):
            continue
        component = getattr(module, key, None)
        if not component:
            continue
        if isinstance(component, HierarchicalGraphMachine):
            machine = component
            logging.info(f"Machine => {machine}")
            break
    else:
        logging.error(f"No HierarchicalGraphMachine object in {args.src}")
        return

    machine.get_graph().draw(module_name, prog="dot", format=args.format)
    if args.format == "xml":
        with open(f"{module_name}.json0", "r") as f:
            input = f.read()


if __name__ == "__main__":
    main()
