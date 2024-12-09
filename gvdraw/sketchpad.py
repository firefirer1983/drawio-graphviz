from abc import abstractmethod
import logging
from functools import wraps
from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Callable, Deque, Generator, Optional, List, Tuple, Any, Dict
from tkinter import *
from tkinter import ttk

Pos = Tuple[int, int]

logger = logging.getLogger(__name__)

hint_box: Optional[int] = None

CHILD_SEP = "."

CANVA_TOP_BUTTON_REGION_HEIGHT = 20


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

    def __repr__(self) -> str:
        return f"{self.source_port} -> {self.target_port}"


transition_registry: List[Transition] = list()


def register_transition(source_port: Port, target_port: Port):
    tx = Transition(source_port, target_port)
    logger.info(f"ADD {tx}")
    transition_registry.append(tx)


class Pole:
    North: int = 0
    East: int = 1
    South: int = 2
    West: int = 3


class EditState:
    Draw = "Draw"
    Moving = "Moving"
    Transition = "Transition"


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

    def __repr__(self) -> str:
        return f"Region<({self.x},{self.y}) {self.width}x{self.height}>"

    def __str__(self) -> str:
        return repr(self)


class Node(Region):
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        tag_id: int,
    ):
        super().__init__(x, y, width, height)
        self.tag_id = tag_id
        self.parent: Optional[Node] = None
        self.children: List[Node] = list()
        self.title_id: Optional[int] = None
        self.ports: List[int] = list()

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
        return f"Node_{self.tag_id} <({self.x},{self.y}) {self.width}x{self.height}>"

    def get_region(self) -> Region:
        return Region(self.x, self.y, self.width, self.height)

    def offset(self, hoffset: int, voffset: int):
        return super().offset(hoffset, voffset)

    def clone(self) -> "Node":
        return Node(self.x, self.y, self.width, self.height, self.tag_id)


@dataclass
class RuntimeEnv:
    root: Tk
    canvas: Canvas
    tree = Node(0, 0, 1920, 1080, 0)
    edit: str = EditState.Draw
    source_port: Optional[Port] = None
    target_port: Optional[Port] = None
    box: Optional[int] = None
    line: Optional[int] = None

    def run(self):
        return self.root.mainloop()


def prepare_runtime():
    root = Tk()
    h = ttk.Scrollbar(root, orient=HORIZONTAL)
    v = ttk.Scrollbar(root, orient=VERTICAL)
    canvas = Canvas(
        root,
        scrollregion=(0, 0, 1000, 1000),
        yscrollcommand=v.set,
        xscrollcommand=h.set,
    )
    h["command"] = canvas.xview
    v["command"] = canvas.yview

    canvas.grid(column=0, row=0, sticky=(N, W, E, S))
    h.grid(column=0, row=1, sticky=(W, E))
    v.grid(column=1, row=0, sticky=(N, S))
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    return RuntimeEnv(root, canvas)


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


class CanvasButton:
    def __init__(self, canvas, x, y, width, height, text):
        button_region_registry.append(Region(x, y, width, height))
        self.canvas = canvas
        self.origin_color = "gray"
        # 创建矩形作为按钮背景
        self.rect = canvas.create_rectangle(
            x, y, x + width, y + height, fill=self.origin_color, outline="black"
        )

        # 创建文本标签
        self.text = canvas.create_text(
            x + width / 2,
            y + height / 2,
            text=text,
            font=("Arial", 8, "bold"),
            fill="black",
        )

        # 绑定鼠标事件

        canvas.tag_bind(self.rect, "<ButtonPress-1>", self.on_press)
        canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)

        canvas.tag_bind(self.text, "<ButtonPress-1>", self.on_press)
        canvas.tag_bind(self.text, "<ButtonRelease-1>", self.on_release)

    @abstractmethod
    def on_press(self, event) -> Optional[str]:
        pass

    @abstractmethod
    def on_release(self, event) -> Optional[str]:
        pass


class MoveButton(CanvasButton):
    def __init__(self, canvas, x, y, width, height):
        super().__init__(canvas, x, y, width, height, "move")

    def on_press(self, event):
        logger.info(f"{runtime.edit} @{self.__class__.__name__} on press!")
        if runtime.edit == EditState.Moving:
            runtime.edit = EditState.Draw
        else:
            runtime.edit = EditState.Moving

        if runtime.edit == EditState.Moving:
            self.canvas.itemconfig(self.rect, fill="yellow")  # 改变颜色以模拟按下效果
        return "break"

    def on_release(self, event):
        logger.info(f"{runtime.edit} @{self.__class__.__name__} on release!")
        if runtime.edit != EditState.Moving:
            self.canvas.itemconfig(self.rect, fill=self.origin_color)  # 恢复原始颜色
        return "break"


class TransitionButton(CanvasButton):
    def __init__(self, canvas, x, y, width, height):
        super().__init__(canvas, x, y, width, height, "trans")

    def on_press(self, event):
        logger.info(f"{runtime.edit} @{self.__class__.__name__} on press!")
        if runtime.edit == EditState.Transition:
            runtime.edit = EditState.Draw
        else:
            runtime.edit = EditState.Transition

        if runtime.edit == EditState.Transition:
            self.canvas.itemconfig(self.rect, fill="yellow")  # 改变颜色以模拟按下效果
            PortVisitor(True).visit(runtime.tree)
        return "break"

    def on_release(self, event):
        logger.info(f"{runtime.edit} @ {self.__class__.__name__} on release!")
        if runtime.edit != EditState.Transition:
            self.canvas.itemconfig(self.rect, fill=self.origin_color)  # 恢复原始颜色
            PortVisitor(False).visit(runtime.tree)
        return "break"


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


move_btn = MoveButton(runtime.canvas, 0, 0, 35, CANVA_TOP_BUTTON_REGION_HEIGHT)
trans_btn = TransitionButton(runtime.canvas, 38, 0, 35, CANVA_TOP_BUTTON_REGION_HEIGHT)

event_registry = defaultdict()


class EventRegistry:
    def __init_subclass__(cls) -> None:
        edit, *_ = cls.__name__.split("EventHandler")
        edit = edit.lower()
        handler = cls()
        logger.info(f"registry[{edit}] = {cls.__name__}")
        event_registry[edit] = handler

    def on_click(self, event):
        mp.pos = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)


class MovingEventHandler(EventRegistry):
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


class DrawEventHandler(EventRegistry):
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
        tag_id = runtime.canvas.create_rectangle(
            (*mp.pos, x, y), fill="", outline="black"
        )
        node = Node(*mp.pos, width, height, tag_id)
        logger.info(f"[NEW]: {node}")

        parent = get_parent(node)
        for c in parent.children:
            logger.info(f"{node} vs {c}")
            if detect_collision(node, c):
                if node == c:
                    continue
                logger.warning(f"检测到碰撞! {node} and {c}")
                runtime.canvas.delete(tag_id)
                return
        parent.add_child(node)
        # 修正node的sibling的父子关系
        for c in parent.children:
            if node.is_child(c):
                node.add_child(c)
                parent.remove_child(c)
        LabelVisitor().visit(node)


class TransitionEventHandler(EventRegistry):
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
        runtime.canvas.create_line(*mp.pos, *pos, fill="black", width=2)
        register_transition(runtime.source_port, runtime.target_port)
        runtime.source_port = runtime.target_port = None
        mp.pos = pos

    def on_move(self, event):
        if runtime.line:
            runtime.canvas.delete(runtime.line)
        x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        runtime.line = runtime.canvas.create_line(*mp.pos, x, y, fill="yellow", width=2)


def button_event_bypass(f: Callable):
    @wraps(f)
    def _wrapper(event):
        x, y = runtime.canvas.canvasy(event.x), runtime.canvas.canvasy(event.y)
        for r in button_region_registry:
            if is_inside((x, y), r):
                logger.warning(f"({x},{y}) in {r}")
                return
        return f(event)

    return _wrapper


@button_event_bypass
def on_click(event):
    eventhandler = event_registry[runtime.edit.lower()]
    eventhandler.on_click(event)


@button_event_bypass
def on_move(event):
    eventhandler = event_registry[runtime.edit.lower()]
    eventhandler.on_move(event)


@button_event_bypass
def on_release(event):
    eventhandler = event_registry[runtime.edit.lower()]
    eventhandler.on_release(event)


class NotImplementVisitor:
    def __call__(self, node: Node, *args: Any, **kwds: Any) -> Any:
        raise SyntaxError(f"visit_{node.__class__.__name__} 未实现")


class DFSVisitor:
    def visit(self, node: Node):
        visit_method = f"visit_{node.__class__.__name__}".lower()
        visitor = getattr(self, visit_method, NotImplementVisitor())
        for child in node.children:
            self.visit(child)
        visitor(node)


class LabelVisitor(DFSVisitor):
    def visit_node(self, node: Node):
        if node.title_id:
            runtime.canvas.delete(node.title_id)
        label = f"{int(node.x)},{int(node.y)}"
        node.title_id = runtime.canvas.create_text(
            node.x + NODE_LABEL_X_OFFSET,
            node.y + NODE_LABEL_Y_OFFSET,
            text=label,
            font=("Arial", 10, "bold"),
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
        runtime.canvas.coords(node.tag_id, node.left, node.top, node.right, node.bottom)
        LabelVisitor().visit_node(node)


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


runtime.canvas.bind("<ButtonPress-1>", on_click)
runtime.canvas.bind("<B1-Motion>", on_move)
runtime.canvas.bind("<ButtonRelease-1>", on_release)


runtime.run()
