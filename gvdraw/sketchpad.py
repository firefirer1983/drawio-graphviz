import json
import click
from abc import abstractmethod
import pprint
import logging
import textwrap
from io import StringIO
from gvdraw.spline import draw_smooth_curve
from gvdraw.bezier import cubic_bezier_points
from functools import wraps, partial
from dataclasses import InitVar, dataclass, field
from collections import defaultdict, deque
from gvdraw.dpi import (
    dpi72todpi96,
    array72todpi96,
    inch2pixel,
    tuples72todpi96,
    tuple72todpi96,
)
from typing import (
    Callable,
    Deque,
    Generator,
    Optional,
    List,
    Tuple,
    Any,
    Dict,
    Set,
    Union,
    Type,
)

from transitions.extensions import HierarchicalGraphMachine
from transitions.extensions.nesting import NestedState
import graphviz

# from tkinter import *
import tkinter as tk
from tkinter import ttk

Pos = Tuple[int, int]

logger = logging.getLogger(__name__)

hint_box: Optional[int] = None

CHILD_SEP = "."


@click.group
class cli:
    pass


@dataclass
class Port:
    node: "Node"
    pole_id: int

    @property
    def pos(self) -> Pos:
        return self.node.pole(self.pole_id)

    def __repr__(self) -> str:
        return f"Port<{self.node} @ {self.pos}>"

    def __str__(self) -> str:
        return repr(self)



@dataclass
class Transition:
    source_port: Port
    target_port: Port
    conditions: Set[str] = field(default_factory=set)
    unless: Set[str] = field(default_factory=set)
    widget: Optional["TransitionWidget"] = None

    def __repr__(self) -> str:
        return f"{self.source_port} -> {self.target_port}"

    def __eq__(self, other) -> bool:
        if isinstance(other, Transition):
            return (
                self.source_port == other.source_port
                and self.target_port == other.target_port
            )
        return False

    @property
    def source(self) -> str:
        return self.source_port.node.label

    @property
    def dest(self) -> str:
        return self.target_port.node.label

    def start_at(self, node: "Node"):
        return self.source_port.node == node

    def end_at(self, node: "Node"):
        return self.target_port.node == node

    def draw(self):
        if not self.widget:
            logger.warning(f"Transtion未关联任何UI Widge")
            return
        self.widget.draw(self.source_port.pos, self.target_port.pos)


transition_registry: List[Transition] = list()


class TransitionWidget:
    def __init__(self, tx: Transition):
        self.tx = tx
        self.tx.widget = self
        self.line_id: Optional[int] = None
        self.arrow_id: Optional[int] = None

    def draw(self, start: Pos, end: Pos):
        x, y = end
        if self.line_id:
            runtime.canvas.delete(self.line_id)
        if self.arrow_id:
            runtime.canvas.delete(self.arrow_id)

        self.line_id = runtime.canvas.create_line(*start, *end, fill="black", width=2)

        # self.arrow_id = runtime.canvas.create_polygon(
        #     x,
        #     y,
        #     x - ARROW_WIDTH,
        #     y - ARROW_HEIGHT,
        #     x + ARROW_WIDTH,
        #     y - ARROW_HEIGHT,
        #     fill="black",
        #     width=2,
        # )
        self.arrow_id = runtime.canvas.create_oval(
            x - PORT_RADIUS,
            y - PORT_RADIUS,
            x + PORT_RADIUS,
            y + PORT_RADIUS,
            fill="black",
            width=2,
        )
        runtime.canvas.tag_bind(self.line_id, "<ButtonPress-1>", self.on_click_btn1)
        runtime.canvas.tag_bind(self.line_id, "<ButtonRelease-1>", self.on_release_btn1)

        runtime.canvas.tag_bind(self.line_id, "<ButtonPress-3>", self.on_click_btn3)
        runtime.canvas.tag_bind(self.line_id, "<ButtonRelease-3>", self.on_release_btn3)

    def on_click_btn1(self, event):
        logger.info(f"TransitionWidget on click btn1")
        return "break"

    def on_release_btn1(self, event):
        logger.info(f"TransitionWidget on release btn1")
        return "break"

    def on_click_btn3(self, event):
        logger.info(f"TransitionWidget on click btn3")
        popup = tk.Toplevel(runtime.canvas)
        popup.title("Multi-input Dialog")

        # 使用 grid 布局管理器
        for i in range(4):  # 设置3行
            popup.grid_rowconfigure(i, weight=1)
        for i in range(2):  # 设置2列
            popup.grid_columnconfigure(i, weight=1)

        # 第一个输入框标签和输入框
        label1 = tk.Label(popup, text="Conditions:")
        label1.grid(row=1, column=0, sticky=tk.W, padx=10, pady=(10, 0))

        conditions_entry = tk.Entry(popup)
        conditions_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10)

        label2 = tk.Label(popup, text="Unless:")
        label2.grid(row=2, column=0, sticky=tk.W, padx=10, pady=(10, 0))

        unless_entry = tk.Entry(popup)
        unless_entry.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=10)

        # 添加提交按钮
        def submit():
            conditions_entries = conditions_entry.get()
            logger.info(f"Conditions: {conditions_entries}")
            for s in conditions_entries.split(","):
                self.tx.conditions.add(s)
            unless_entries = unless_entry.get()
            logger.info(f"Unless: {unless_entries}")
            for s in unless_entries.split(","):
                self.tx.unless.add(s)
            popup.destroy()  # 关闭弹出框

        submit_button = tk.Button(popup, text="确认", command=submit)
        submit_button.grid(row=4, column=0, columnspan=2, pady=10)
        return "break"

    def on_release_btn3(self, event):
        logger.info(f"TransitionWidget on release btn3")
        logger.info(f"{self.tx} on release btn3")
        return "break"


class NodeWidget:
    def __init__(self, node: "Node"):
        self.node = node
        self.tag_id = runtime.canvas.create_rectangle(
            (self.node.left, self.node.top, self.node.right, self.node.bottom),
            fill="",
            outline="black",
        )
        logger.info(
            f"[NODE] ({self.node.left}, {self.node.top}) {self.node.right - self.node.left}x{self.node.bottom - self.node.top}"
        )
        self.label_id = runtime.canvas.create_text(
            node.x + NODE_LABEL_X_OFFSET,
            node.y + NODE_LABEL_Y_OFFSET,
            text=node.label,
            font=("Arial", runtime.fontsize, "bold"),
        )

    def draw(self):
        if self.tag_id:
            runtime.canvas.delete(self.tag_id)
        self.tag_id = runtime.canvas.create_rectangle(
            (self.node.left, self.node.top, self.node.right, self.node.bottom),
            fill="",
            outline="black",
        )
        self.label()

    def label(self):
        if self.label_id:
            runtime.canvas.delete(self.label_id)
        self.label_id = runtime.canvas.create_text(
            self.node.x + NODE_LABEL_X_OFFSET,
            self.node.y + NODE_LABEL_Y_OFFSET,
            text=self.node.label,
            font=("Arial", runtime.fontsize, "bold"),
        )

    def on_click_btn1(self, event):
        pass

    def on_release_btn1(self, event):
        pass

    def on_click_btn3(self, event):
        pass

    def on_release_btn3(self, event):
        pass


def register_transition(source_port: Port, target_port: Port) -> Transition:
    tx = Transition(source_port, target_port)
    tx.widget = TransitionWidget(tx)
    logger.info(f"ADD {tx}")
    transition_registry.append(tx)
    return tx


class Pole:
    North: int = 0
    East: int = 1
    South: int = 2
    West: int = 3


class CanvasMode:
    Browse = "Browse"
    Draw = "Draw"
    Moving = "Moving"
    Transition = "Transition"
    Export = "Export"


class Region:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x, self.y, self.width, self.height = x, y, width, height

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def size(self) -> int:
        return self.width * self.height

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def poles(self) -> Generator[Pos, None, None]:
        hmid = self.x + self.width // 2
        vmid = self.y + self.height // 2
        yield hmid, self.top
        yield self.x + self.width, vmid
        yield hmid, self.y + self.height
        yield self.x, vmid

    def pole(self, pid: int) -> Pos:
        return list(self.poles)[pid]

    @property
    def corners(self) -> Generator[Pos, None, None]:
        # 按照顺时针方向返回4个角
        yield (self.left, self.top)
        yield (self.right, self.top)
        yield (self.right, self.bottom)
        yield (self.left, self.bottom)

    def offset(self, hoffset: int, voffset: int):
        self.x += int(hoffset)
        self.y += int(voffset)
        return self

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Region<({self.x},{self.y}) {self.width}x{self.height}>"

    def __str__(self) -> str:
        return repr(self)


UNIQUE_CODES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Node(Region):
    sequence_id = 0

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ):
        super().__init__(x, y, width, height)
        self.widget: Optional[NodeWidget] = None
        self.parent: Optional[Node] = None
        self.children: List[Node] = list()
        self.title_id: Optional[int] = None
        self.ports: List[int] = list()
        self.on_enter: Set[str] = set()
        self.on_exit: Set[str] = set()

        n = Node.sequence_id // len(UNIQUE_CODES)
        l = Node.sequence_id % len(UNIQUE_CODES)
        self.unique_id = UNIQUE_CODES[l]
        while n:
            n = n // len(UNIQUE_CODES)
            l = n % len(UNIQUE_CODES)
            self.unique_id += UNIQUE_CODES[l]

        Node.sequence_id += 1
        logger.info(f"UNIQUE ID: {self.unique_id}")

    @property
    def tag_id(self) -> int:
        if self.widget:
            return self.widget.tag_id
        raise RuntimeError

    def draw(self) -> NodeWidget:
        if self.widget:
            self.widget.draw()
        else:
            self.widget = NodeWidget(self)
        return self.widget

    def add_child(self, child: "Node"):
        if child in self.children:
            return
        self.children.append(child)
        child.parent = self

    def remove_child(self, child: "Node"):
        self.children = [c for c in self.children if c != child]

    def is_child(self, child: "Node") -> bool:
        """(left,top) && (right, bottom) 都在其内部，就为其 Child Node"""
        return is_inside((child.left, child.top), self) and is_inside(
            (child.right, child.bottom), self
        )

    def __repr__(self) -> str:
        return f"Node <({self.x},{self.y}) {self.width}x{self.height}>"

    def get_region(self) -> Region:
        return Region(self.x, self.y, self.width, self.height)

    def offset(self, hoffset: int, voffset: int):
        return super().offset(hoffset, voffset)

    def clone(self) -> "Node":
        return Node(self.x, self.y, self.width, self.height)

    def add_on_enter(self, func: str):
        self.on_enter.add(func)

    def add_on_exit(self, func: str):
        self.on_exit.add(func)

    @property
    def label(self) -> str:
        return self.unique_id

    @label.setter
    def label(self, value):
        # need to double check
        self.unique_id = value

    @property
    def is_root(self) -> bool:
        return self.parent is None


DEFAULT_FONT_SIZE = 10


@dataclass
class RuntimeEnv:
    root: tk.Tk
    top_frame: tk.Frame
    canvas_frame: tk.Frame
    canvas: tk.Canvas
    tree: Node
    canvas_mode: str = CanvasMode.Browse
    source_port: Optional[Port] = None
    target_port: Optional[Port] = None
    box: Optional[int] = None
    line: Optional[int] = None
    scale_factor: float = 1.0

    def run(self):
        return self.root.mainloop()

    @property
    def fontsize(self) -> int:
        return int(DEFAULT_FONT_SIZE * self.scale_factor)


def prepare_runtime():
    root = tk.Tk()
    root.title("Gvdraw")

    canvas = tk.Canvas(
        root,
    )
    top_frame = tk.Frame(root, bg="lightgray")
    canvas_frame = tk.Frame(root)

    # 创建 Canvas 并放置在画布框架中
    canvas = tk.Canvas(canvas_frame, bg="white")
    canvas.pack(fill=tk.BOTH, expand=True)

    return RuntimeEnv(root, top_frame, canvas_frame, canvas, Node(0, 0, 1920, 1080))


runtime = prepare_runtime()


def is_inside(pos: Pos, node: "Region"):
    x, y = pos
    return x > node.left and x < node.right and y > node.top and y < node.bottom


def detect_collision(first: "Region", second: "Region") -> bool:
    insides = 0
    for pos in first.corners:
        if is_inside(pos, second):
            insides += 1
    if insides and insides <= 2:
        return True
    insides = 0
    for pos in second.corners:
        if is_inside(pos, first):
            insides += 1
    if insides and insides <= 2:
        return True
    return False


def get_node(pos: Pos, node: Node) -> Optional[Node]:
    def _iter_children(pos, node: Node) -> Optional[Node]:
        if not is_inside(pos, node):
            return
        for c in node.children:
            if is_inside(pos, c):
                return _iter_children(pos, c)
        return node

    return _iter_children(pos, node)


def get_parent(node: Node) -> Node:
    def _get_parent(parent: Node, child: Node) -> Optional[Node]:
        if not parent.is_child(child):
            logger.info(f"{parent} is not {child}'s parent")
            return
        for n in parent.children:
            result = _get_parent(n, child)
            if not result:
                continue
            return result
        logger.info(f"{parent} is {child}'s parent")
        return parent

    return _get_parent(runtime.tree, node) or runtime.tree


button_region_registry: List[Region] = list()


# class CanvasButtonBase:
#     def __init__(self, canvas, x, y, width, height, text):
#         button_region_registry.append(Region(x, y, width, height))
#         self.canvas = canvas
#         self.origin_color = "gray"
#         # 创建矩形作为按钮背景
#         self.rect = canvas.create_rectangle(
#             x, y, x + width, y + height, fill=self.origin_color, outline="black"
#         )

#         # 创建文本标签
#         self.text = canvas.create_text(
#             x + width / 2,
#             y + height / 2,
#             text=text,
#             font=("Arial", 8, "bold"),
#             fill="black",
#         )

#         # 绑定鼠标事件

#         canvas.tag_bind(self.rect, "<ButtonPress-1>", self.on_press)
#         canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)

#         canvas.tag_bind(self.text, "<ButtonPress-1>", self.on_press)
#         canvas.tag_bind(self.text, "<ButtonRelease-1>", self.on_release)

#     @abstractmethod
#     def on_press(self, event) -> Optional[str]:
#         pass

#     @abstractmethod
#     def on_release(self, event) -> Optional[str]:
#         pass

BTN_WIDTH = 42
BTN_HEIGHT = 20


class MoveButton(tk.Button):
    def __init__(self, parent):
        super().__init__(master=parent, text="move", command=self.on_press)

    def on_press(self):
        logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
        if runtime.canvas_mode == CanvasMode.Moving:
            runtime.canvas_mode = CanvasMode.Browse
        else:
            runtime.canvas_mode = CanvasMode.Moving
        return "break"


class TransitionButton(tk.Button):
    def __init__(self, parent):
        super().__init__(parent, text="trans", command=self.on_press)

    def on_press(self):
        logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
        if runtime.canvas_mode == CanvasMode.Transition:
            runtime.canvas_mode = CanvasMode.Browse
        else:
            runtime.canvas_mode = CanvasMode.Transition

        if runtime.canvas_mode == CanvasMode.Transition:
            PortVisitor(True).visit(runtime.tree)
        return "break"


class ExportButton(tk.Button):
    def __init__(self, parent):
        super().__init__(parent, text="export", command=self.on_press)

    def on_press(self):
        logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
        logger.info(f"Start Exporting ...")
        return "break"


# class MoveButton(CanvasButtonBase):
#     def __init__(self, canvas, x, y, width, height):
#         super().__init__(canvas, x, y, width, height, "move")

#     def on_press(self, event):
#         logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
#         if runtime.canvas_mode == CanvasMode.Moving:
#             runtime.canvas_mode = CanvasMode.Browse
#         else:
#             runtime.canvas_mode = CanvasMode.Moving

#         if runtime.canvas_mode == CanvasMode.Moving:
#             self.canvas.itemconfig(self.rect, fill="yellow")  # 改变颜色以模拟按下效果
#         return "break"

#     def on_release(self, event):
#         logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on release!")
#         if runtime.canvas_mode != CanvasMode.Moving:
#             self.canvas.itemconfig(self.rect, fill=self.origin_color)  # 恢复原始颜色
#         return "break"


# class TransitionButton(CanvasButtonBase):
#     def __init__(self, canvas, x, y, width, height):
#         super().__init__(canvas, x, y, width, height, "trans")

#     def on_press(self, event):
#         logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
#         if runtime.canvas_mode == CanvasMode.Transition:
#             runtime.canvas_mode = CanvasMode.Browse
#         else:
#             runtime.canvas_mode = CanvasMode.Transition

#         if runtime.canvas_mode == CanvasMode.Transition:
#             self.canvas.itemconfig(self.rect, fill="yellow")  # 改变颜色以模拟按下效果
#             PortVisitor(True).visit(runtime.tree)
#         return "break"

#     def on_release(self, event):
#         logger.info(f"{runtime.canvas_mode} @ {self.__class__.__name__} on release!")
#         if runtime.canvas_mode != CanvasMode.Transition:
#             self.canvas.itemconfig(self.rect, fill=self.origin_color)  # 恢复原始颜色
#             PortVisitor(False).visit(runtime.tree)
#         return "break"


# class ExportButton(CanvasButtonBase):
#     def __init__(self, canvas, x, y, width, height):
#         super().__init__(canvas, x, y, width, height, "export")

#     def on_press(self, event):
#         logger.info(f"{runtime.canvas_mode} @{self.__class__.__name__} on press!")
#         logger.info(f"Start Exporting ...")
#         return "break"

#     def on_release(self, event):
#         logger.info(f"{runtime.canvas_mode} @ {self.__class__.__name__} on release!")


@dataclass
class MousePoint:
    x: int = 0
    y: int = 0

    @property
    def pos(self) -> Tuple[int, int]:
        return self.x, self.y

    @pos.setter
    def pos(self, pos: Tuple[int, int]):
        self.x, self.y = pos

    def __repr__(self) -> str:
        return f"{self.pos}"

    def __str__(self) -> str:
        return repr(self)


mp = MousePoint()

NODE_LABEL_X_OFFSET = 20
NODE_LABEL_Y_OFFSET = 7


event_registry = defaultdict()


class EventRegistry:
    def __init_subclass__(cls) -> None:
        edit, *_ = cls.__name__.split("CanvasHandler")
        edit = edit.lower()
        handler = cls()
        logger.info(f"registry[{edit}] = {cls.__name__}")
        event_registry[edit] = handler

    def on_click(self, event):
        mp.pos = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)


class BrowseCanvasHandler(EventRegistry):
    def on_click(self, event):
        mp.pos = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)

    def on_move(self, event):
        if mp.x is not None and mp.y is not None:
            dx = runtime.canvas.canvasx(event.x) - mp.x
            dy = runtime.canvas.canvasy(event.y) - mp.y
            runtime.canvas.move("all", dx, dy)
            mp.x = runtime.canvas.canvasx(event.x)
            mp.y = runtime.canvas.canvasy(event.y)

    def on_release(self, event):
        pass

    def on_roll(self, event):
        """
        Zoom Up/Down
        """
        logger.info(f"[Rolling]: {event.num}")
        if event.num == 5 or event.delta == -120:  # 向下滚动或 Linux 下滚
            factor = 0.9
        elif event.num == 4 or event.delta == 120:  # 向上滚动或 Linux 上滚
            factor = 1.1
        else:
            return

        runtime.scale_factor *= factor

        # 缩放围绕鼠标指针进行
        x = runtime.canvas.canvasx(event.x)
        y = runtime.canvas.canvasy(event.y)

        runtime.canvas.scale("all", x, y, factor, factor)

        # 更新所有对象的坐标
        for item in runtime.canvas.find_all():
            coords = runtime.canvas.coords(item)
            new_coords = [coord * factor for coord in coords]
            runtime.canvas.coords(item, *new_coords)


class MovingCanvasHandler(EventRegistry):
    def on_move(self, event):
        pass

    def on_release(self, event):
        x, y = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)
        node = get_node((mp.x, mp.y), runtime.tree)
        if not (node and node.parent):
            return
        logger.info(f"[TOUCHED]: {node}")
        hoffset, voffset = x - mp.x, y - mp.y
        logger.info(f"Origin: {node}")
        probe = node.clone()
        probe.offset(hoffset, voffset)
        logger.info(f"Offset by H:{hoffset}, V:{voffset} => {probe}")
        parent = get_parent(probe)
        for c in parent.children:
            if node == c:
                continue
            if detect_collision(probe, c):
                logger.warning(f"Collision Detected!: {probe} vs {c} !")
                return
        node.parent.remove_child(node)
        parent.add_child(node)

        OffsetVisitor(hoffset, voffset).visit(node)
        return


class DrawCanvasHandler(EventRegistry):
    def on_click(self, event):
        mp.pos = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)

    def on_move(self, event):
        x, y = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)
        if runtime.box:
            runtime.canvas.delete(runtime.box)
        runtime.box = runtime.canvas.create_rectangle(
            (*mp.pos, x, y), fill="", outline="yellow"
        )

    def on_release(self, event):
        x, y = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)

        if runtime.box:
            runtime.canvas.delete(runtime.box)
            runtime.box = None

        if x == mp.x and y == mp.y:
            logger.warning(f"SIZE 0")
            return

        width, height = x - mp.x, y - mp.y
        node = Node(*mp.pos, width, height)
        logger.info(f"[NEW]: {node}")

        parent = get_parent(node)
        for c in parent.children:
            logger.info(f"{node} vs {c}")
            if detect_collision(node, c):
                if node == c:
                    continue
                logger.warning(f"检测到碰撞! {node} and {c}")
                return
        node.draw()
        parent.add_child(node)
        # 修正node的sibling的父子关系
        for c in parent.children:
            if node.is_child(c):
                node.add_child(c)
                parent.remove_child(c)
        LabelVisitor().visit(node)


class TransitionCanvasHandler(EventRegistry):
    def on_click(self, event):
        x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        port = get_select_port(x, y)
        if not port:
            logger.warning(f"未选中任何Port: ({x},{y})")
            return
        runtime.source_port, mp.pos = port, port.pos

    def on_release(self, event):
        if runtime.line:
            runtime.canvas.delete(runtime.line)
        if not runtime.source_port:
            logger.warning(f"未选中任何 source port")
            return

        x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        port = get_select_port(x, y)
        if not port:
            logger.warning(f"未选中任何 target node")
            return
        runtime.target_port, pos = port, port.pos
        tx = register_transition(runtime.source_port, runtime.target_port)
        tx.draw()
        runtime.source_port = runtime.target_port = None
        mp.pos = pos

    def on_move(self, event):
        if runtime.line:
            runtime.canvas.delete(runtime.line)
        x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        runtime.line = runtime.canvas.create_line(*mp.pos, x, y, fill="yellow", width=2)


class AttrCanvasHandler(EventRegistry):
    def on_click(self, event):
        mp.pos = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        elements = [_ for _ in runtime.canvas.find_all()]
        for tag_id in elements:
            logger.info(f"{tag_id}")

    def on_release(self, event):
        pass

    def on_move(self, event):
        pass


# def button_event_bypass(f: Callable):
#     @wraps(f)
#     def _wrapper(event):
#         x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
#         for r in button_region_registry:
#             if is_inside((x, y), r):
#                 logger.warning(f"({x},{y}) in {r}")
#                 return
#         return f(event)

#     return _wrapper


def on_click(event):
    logger.info(f"[OnClick] {event} @ {runtime.canvas_mode.lower()}")
    eventhandler = event_registry[runtime.canvas_mode.lower()]
    eventhandler.on_click(event)


def on_roll(event):
    logger.info(f"[OnRoll] {event} @ {runtime.canvas_mode.lower()}")
    eventhandler = event_registry[runtime.canvas_mode.lower()]
    eventhandler.on_roll(event)


def on_move(event):
    logger.info(f"[OnMove] {event} @ {runtime.canvas_mode.lower()}")
    eventhandler = event_registry[runtime.canvas_mode.lower()]
    eventhandler.on_move(event)


def on_release(event):
    logger.info(f"[OnRelease] {event} @ {runtime.canvas_mode.lower()}")
    eventhandler = event_registry[runtime.canvas_mode.lower()]
    eventhandler.on_release(event)


class NotImplementVisitor:
    def __call__(self, node: Node, *args: Any, **kwds: Any) -> Any:
        raise SyntaxError(f"visit_{node.__class__.__name__} 未实现")


class DFSVisitor:
    def visit(self, node: Node):
        visit_method = f"visit_{node.__class__.__name__}".lower()
        visitor = getattr(self, visit_method, NotImplementVisitor())
        q: Deque[Node] = deque([node])
        while q:
            n = q.pop()
            visitor(n)
            for c in n.children:
                q.append(c)

        # for child in node.children:
        #     self.visit(child)
        # visitor(node)


class BFSVisitor:
    def visit(self, node: Node):
        visit_method = f"visit_{node.__class__.__name__}".lower()
        visitor = getattr(self, visit_method, NotImplementVisitor())
        q: Deque[Node] = deque([node])
        while q:
            n = q.popleft()
            visitor(n)
            for c in n.children:
                q.append(c)


class LabelVisitor(DFSVisitor):
    # def visit_node(self, node: Node):
    #     if node.title_id:
    #         runtime.canvas.delete(node.title_id)
    #     label = f"{int(node.x)},{int(node.y)}"
    #     node.title_id = runtime.canvas.create_text(
    #         node.x + NODE_LABEL_X_OFFSET,
    #         node.y + NODE_LABEL_Y_OFFSET,
    #         text=label,
    #         font=("Arial", 10, "bold"),
    #     )

    def visit_node(self, node: Node):
        if node.title_id:
            runtime.canvas.delete(node.title_id)

        parent = node.parent
        label = f"{node.label}"
        # while parent:
        #     if parent is runtime.tree:
        #         break
        #     label = f"{parent.label}" + CHILD_SEP + f"{label}"
        #     parent = parent.parent
        #     logger.info(f"parent: {parent}")

        node.title_id = runtime.canvas.create_text(
            node.x + NODE_LABEL_X_OFFSET,
            node.y + NODE_LABEL_Y_OFFSET,
            text=label,
            font=("Arial", runtime.fontsize, "bold"),
        )

    # def visit_node(self, node: Node):
    #     if node.title_id:
    #         runtime.canvas.delete(node.title_id)

    #     parent = node.parent
    #     label = f"{node.tag_id}"
    #     while parent:
    #         label = f"{parent.tag_id}" + CHILD_SEP + f"{label}"
    #         parent = parent.parent
    #         logger.info(f"parent: {parent}")

    #     node.title_id = runtime.canvas.create_text(
    #         node.x + NODE_LABEL_X_OFFSET,
    #         node.y + NODE_LABEL_Y_OFFSET,
    #         text=label,
    #         font=("Arial", 10, "bold"),
    #     )


class OffsetVisitor(DFSVisitor):
    def __init__(self, hoffset: int, voffset: int):
        self.hoffset = hoffset
        self.voffset = voffset

    def visit_node(self, node: Node):
        node.x += int(self.hoffset)
        node.y += int(self.voffset)
        node.draw()
        for tx in transition_registry:
            if tx.start_at(node) or tx.end_at(node):
                tx.draw()
        LabelVisitor().visit_node(node)


ARROW_WIDTH = 3
ARROW_HEIGHT = 8


class StateEnumExporter(BFSVisitor):
    header = "class States(StateEnum):\n"

    def __init__(self):
        self.buf = StringIO()

    def visit_node(self, node: Node):
        return self.buf.write(f' {node.label}: str = "{ node.label }"')

    def build(self) -> str:
        return self.header + textwrap.indent(self.buf.getvalue(), "\t")


PORT_RADIUS = 3

FILL_COLOR = "yellow"
BORDER_COLOR = "black"
BORDER_WIDTH = 1


def get_select_port(x: int, y: int) -> Optional[Port]:
    def _select_port(node: Node) -> Optional[Port]:
        for pole_id, pos in enumerate(node.poles):
            x0, y0 = pos
            if ((x - x0) ** 2 + (y - y0) ** 2) <= PORT_RADIUS**2:
                return Port(node, pole_id)
        for c in node.children:
            n = _select_port(c)
            if not n:
                continue
            return n

    return _select_port(runtime.tree)


class DotVisitor(BFSVisitor):
    def __init__(self):
        self.dot = graphviz.Digraph("sketchpad", format="json0")
        self.dot.node_attr["shape"] = "box"

    def visit_node(self, node: Node):
        self.dot.node(node.label, node.label)


def get_dotnode_type(
    n: dict,
) -> Union[Type["Cluster"], Type["ClusterRoot"], Type["DotNode"]]:
    name: str = n["name"]
    if name.startswith("cluster_") and name.endswith("_root"):
        return ClusterRoot
    elif name.startswith("cluster_"):
        return Cluster
    else:
        return DotNode


@dataclass
class Cluster:
    _gvid: int = field(init=False)
    bb: List[int] = field(init=False)
    color: str = field(init=False)
    directed: bool = field(init=False)
    label: str = field(init=False)
    name: str = field(init=False)
    fillcolor: str = field(init=False)
    style: str = field(init=False)
    rank: str = field(init=False)
    rankdir: str = field(init=False)
    lp: List[int] = field(init=False)
    lwidth: int = field(init=False)
    lheight: int = field(init=False)
    strict: bool = field(init=False)
    nodesep: int = field(init=False)
    compound: bool = field(init=False)
    edges: List[int] = field(init=False)
    nodes: List[int] = field(init=False)
    subgraphs: List[int] = field(init=False)

    dotobj: InitVar[dict]

    def __post_init__(self, dotobj: dict):
        self._gvid = dotobj["_gvid"]
        self.bb = array72todpi96(dotobj["bb"])
        self.color = dotobj["color"]
        self.label = dotobj.get("label", "")
        self.style = dotobj.get("style", "")
        self.name = dotobj.get("name", "")
        self.fillcolor = dotobj["fillcolor"]
        self.compound = bool(dotobj.get("compound") == "true")
        self.directed = bool(dotobj.get("directed") == "true")
        self.lheight = inch2pixel(dotobj["lheight"])
        self.lwidth = inch2pixel(dotobj["lwidth"])
        self.lp = array72todpi96(dotobj["lp"])
        self.nodesep = inch2pixel(dotobj.get("nodesep", 0))
        self.rank = dotobj["rank"]
        self.rankdir = dotobj["rankdir"]
        self.strict = bool(dotobj["strict"] == "true")
        self.edges = dotobj.get("edges", [])
        self.nodes = dotobj.get("nodes", [])
        self.subgraphs = dotobj.get("subgraphs", [])


@dataclass
class ClusterRoot:
    _gvid: int = field(init=False)
    bb: List[int] = field(init=False)
    color: str = field(init=False)
    directed: bool = field(init=False)
    fillcolor: str = field(init=False)
    label: str = field(init=False)
    nodesep: int = field(init=False)
    name: str = field(init=False)
    nodes: List[int] = field(init=False)
    rank: str = field(init=False)
    rankdir: str = field(init=False)
    strict: str = field(init=False)
    style: str = field(init=False)
    compound: bool = field(init=False)
    dotobj: InitVar[dict]

    def __post_init__(self, dotobj: dict):
        self._gvid = dotobj["_gvid"]
        self.name = dotobj["name"]
        self.bb = array72todpi96(dotobj["bb"])
        self.color = dotobj["color"]
        self.compound = bool(dotobj.get("compound") == "true")
        self.directed = bool(dotobj.get("directed") == "true")
        self.fillcolor = dotobj["fillcolor"]
        self.label = dotobj["label"]
        self.nodesep = inch2pixel(dotobj.get("nodesep", 0))
        self.rank = dotobj["rank"]
        self.rankdir = dotobj["rankdir"]
        self.strict = dotobj["strict"]
        self.style = dotobj["style"]
        self.nodes = dotobj["nodes"]


@dataclass
class DotNode:
    _gvid: int = field(init=False)
    label: str = field(init=False)
    name: str = field(init=False)
    color: str = field(init=False)
    fillcolor: str = field(init=False)
    style: str = field(init=False)
    pos: Pos = field(init=False)
    width: int = field(init=False)
    height: int = field(init=False)
    shape: str = field(init=False)
    peripheries: str = field(init=False)

    dotobj: InitVar[dict]

    def __post_init__(self, dotobj: dict):
        self._gvid = int(dotobj["_gvid"])
        self.name = dotobj["name"]
        self.color = dotobj["color"]
        self.fillcolor = dotobj["fillcolor"]
        self.height = inch2pixel(dotobj["height"])
        self.label = dotobj["label"]
        self.peripheries = dotobj["peripheries"]
        self.pos: Pos = tuple72todpi96(dotobj["pos"])
        self.shape = dotobj["shape"]
        self.style = dotobj.get("style", "")
        self.width = inch2pixel(dotobj["width"])


@dataclass
class DotEdge:
    _gvid: int = field(init=False)
    head: int = field(init=False)
    tail: int = field(init=False)
    pos: List[Pos] = field(init=False)
    color: str = field(init=False)
    label: str = field(init=False)
    lhead: str = field(init=False)
    ltail: str = field(init=False)
    lp: List[int] = field(init=False)
    tail_lp: str = field(init=False)
    head_lp: str = field(init=False)
    taillabel: str = field(init=False)
    headlabel: str = field(init=False)

    dotobj: InitVar[dict]

    def __post_init__(self, dotobj: dict):
        self._gvid = dotobj["_gvid"]
        self.tail = dotobj["tail"]
        self.head = dotobj["head"]
        self.color = dotobj["color"]
        self.label = dotobj["label"]
        self.lp = array72todpi96(dotobj["lp"])
        self.pos = tuples72todpi96(dotobj["pos"])
        self.lhead = dotobj.get("lhead", "")
        self.ltail = dotobj.get("ltail", "")
        self.tail_lp = dotobj.get("tail_lp", "")
        self.head_lp = dotobj.get("head_lp", "")
        self.taillabel = dotobj.get("taillabel", "")
        self.headlabel = dotobj.get("headlabel", "")


@dataclass
class DotLayout:
    name: str = field(init=False)
    directed: bool = field(init=False)
    strict: bool = field(init=False)
    bb: List[int] = field(init=False)
    color: str = field(init=False)
    compound: bool = field(init=False)
    directed: bool = field(init=False)
    fillcolor: str = field(init=False)
    label: str = field(init=False)
    lheight: int = field(init=False)
    lp: List[int] = field(init=False)
    lwidth: int = field(init=False)
    nodesep: int = field(init=False)
    # rank: str =  field(init=False)
    rankdir: str = field(init=False)
    strict: bool = field(init=False)
    style: str = field(init=False)
    _subgraph_cnt: int = field(init=False)
    objects: List[Union[Cluster, ClusterRoot, DotNode]] = field(init=False)
    edges: List[DotEdge] = field(init=False)

    dotobj: InitVar[dict]

    def __post_init__(self, dotobj: dict):
        self.name = dotobj["name"]
        self.directed = bool(dotobj.get("directed") == "true")
        self.compound = bool(dotobj.get("compound") == "true")
        self.strict = bool(dotobj.get("strict") == "true")
        self.bb = array72todpi96(dotobj["bb"])
        self.color = dotobj["color"]
        self.fillcolor = dotobj["fillcolor"]
        self.label = dotobj["label"]
        # self.rank = dotobj["rank"]
        self.rankdir = dotobj["rankdir"]
        self.nodesep = dotobj.get("nodesep", 0)
        self.style = dotobj["style"]
        self.lp = array72todpi96(dotobj["lp"])
        self.lwidth = inch2pixel(dotobj["lwidth"])
        self.lheight = inch2pixel(dotobj["lheight"])
        self._subgraph_cnt = dotobj["_subgraph_cnt"]
        self.objects = []

        for obj in dotobj["objects"]:
            objtype = get_dotnode_type(obj)
            self.objects.append(objtype(obj))

        self.edges = [DotEdge(edg) for edg in dotobj["edges"]]


class LayoutImportVisitor:
    def __init__(self, layout: dict, sep: str = "."):
        self.layout = DotLayout(layout)
        self.nodes = self.layout.objects
        self.edges = self.layout.edges


class LayoutExportVisitor:
    from transitions.extensions.nesting import NestedState
    from transitions.extensions.diagrams import HierarchicalGraphMachine

    def __init__(self) -> None:
        self.states = list()
        self.transitions = list()
        self.visit(runtime.tree)
        self.visit_transition()
        self.machine = HierarchicalGraphMachine(
            states=self.states,
            show_conditions=True,
            show_state_attributes=True,
            use_pygraphviz=False,
            transitions=self.transitions,
        )

    def visit(self, node: Node, parent: Optional[NestedState] = None):
        for child in node.children:
            state = NestedState(
                child.label, on_enter=list(child.on_enter), on_exit=list(child.on_exit)
            )
            if parent:
                parent.add_substate(state)
            else:
                self.states.append(state)
            self.visit(child, state)

    def visit_transition(self):
        for tx in transition_registry:
            self.transitions.append(
                dict(
                    source=tx.source,
                    dest=tx.dest,
                    conditions=tx.conditions,
                    unless=tx.unless,
                    trigger="next",
                )
            )

    def layout(self) -> dict:
        graph = self.machine.get_graph()
        graph.attr(rankdir="TB")  # 设置方向为从上到下
        result = graph.draw(None, prog="dot", format="json0")
        layout = json.loads(result.decode("utf8"))
        pprint.pprint(layout)
        return layout


class PortVisitor(DFSVisitor):
    def __init__(self, show: bool = False):
        self.show = show

    def visit_node(self, node: Node):
        if not self.show:
            for port_id in node.ports:
                runtime.canvas.delete(port_id)
            node.ports.clear()
        else:
            radius = PORT_RADIUS
            for x, y in node.poles:
                port_id = runtime.canvas.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill=FILL_COLOR,
                    outline=BORDER_COLOR,
                    width=BORDER_WIDTH,
                )
                node.ports.append(port_id)
                node.ports.append(port_id)

        for c in node.children:
            self.visit(c)


def prepare_layout(env: RuntimeEnv):
    # BTN_WIDTH = 42
    # BTN_HEIGHT = 20
    # BTN_GAP = 3
    # BTN_OFFSET = BTN_GAP + BTN_WIDTH
    # env.canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
    # env.root.grid_columnconfigure(0, weight=1)
    # env.root.grid_rowconfigure(0, weight=1)

    # 配置主窗口的网格布局
    runtime.root.grid_rowconfigure(1, weight=1)
    runtime.root.grid_columnconfigure(0, weight=1)

    # 创建顶部框架用于放置按钮
    runtime.top_frame.grid(row=0, column=0, sticky="ew")

    # 创建画布框架并配置其在网格中的位置
    runtime.canvas_frame.grid(row=1, column=0, sticky="nsew")

    # 配置顶部框架的列权重，使得按钮均匀分布
    runtime.top_frame.grid_columnconfigure((0, 1, 2), weight=1)

    env.canvas.bind("<ButtonPress-1>", on_click)
    env.canvas.bind("<B1-Motion>", on_move)
    env.canvas.bind("<ButtonRelease-1>", on_release)
    env.canvas.bind("<MouseWheel>", on_roll)  # Windows 和 MacOS
    env.canvas.bind("<Button-4>", on_roll)  # Linux 滚轮上滚
    env.canvas.bind("<Button-5>", on_roll)  # Linux 滚轮下滚

    # MoveButton(env.canvas, 0, 0, BTN_WIDTH, BTN_HEIGHT)
    # TransitionButton(env.canvas, BTN_OFFSET, 0, BTN_WIDTH, BTN_HEIGHT)
    # ExportButton(env.canvas, 2 * BTN_OFFSET, 0, BTN_WIDTH, BTN_HEIGHT)

    move_btn = MoveButton(env.top_frame)
    move_btn.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

    trans_btn = TransitionButton(env.top_frame)
    trans_btn.grid(row=0, column=1, padx=0, pady=0, sticky="ew")

    export_btn = ExportButton(env.top_frame)
    export_btn.grid(row=0, column=2, padx=0, pady=0, sticky="ew")


@cli.command
def start():
    prepare_layout(runtime)
    runtime.run()


@cli.command
@click.argument("filename", type=str)
def import_json(filename: str):
    import pprint

    prepare_layout(runtime)

    with open(filename, "r", encoding="utf8") as f:
        dat = f.read()
        dotfile = json.loads(dat)
        logger.info(f"Import : {filename}: \n ")
    pprint.pprint(dotfile)

    visitor = LayoutImportVisitor(dotfile)
    x0, y0, x1, y1 = visitor.layout.bb
    width, height = x1 - x0, y1 - y0
    # runtime.canvas.config(width=width, height=height)
    # runtime.tree.resize(width, height)
    for dotnode in visitor.nodes:
        if isinstance(dotnode, Cluster):
            x0, y0, x1, y1 = dotnode.bb
            width, height = x1 - x0, y1 - y0
            node = Node(x0, y0, width, height)
            _, node.label = dotnode.name.split("cluster_")
            node.draw()
            parent = get_parent(node)
            parent.add_child(node)
        elif isinstance(dotnode, DotNode) and dotnode.shape == "point":
            logger.info(f"IGNORE: {dotnode}")
        elif isinstance(dotnode, DotNode):
            width, height = dotnode.width, dotnode.height
            cx, cy = dotnode.pos
            x0, y0 = cx - width // 2, cy - height // 2
            logger.info(f"{dotnode.name}: ({x0},{y0}) {width}x{height}")
            node = Node(x0, y0, width, height)
            node.label = dotnode.name
            node.draw()
            parent = get_parent(node)
            parent.add_child(node)
        else:
            logger.warning(f"无法处理的节点: {dotnode}")

    for edg in visitor.edges:
        draw_smooth_curve(runtime.canvas, edg.pos)
        # cubic_bezier_points(runtime.canvas, edg.pos)
        logger.info(f"{edg}")

    runtime.run()


if __name__ == "__main__":
    cli()
