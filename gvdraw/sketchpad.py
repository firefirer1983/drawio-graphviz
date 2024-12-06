from abc import abstractmethod
import logging
from dataclasses import dataclass
from collections import deque
from typing import Deque, Generator, Optional, List, Tuple, Any
from tkinter import *
from tkinter import ttk

Pos = Tuple[int, int]

logger = logging.getLogger(__name__)

hint_box: Optional[int] = None

CHILD_SEP = "."


@dataclass
class RuntimeEnv:
    root: Tk
    canvas: Canvas
    moving: bool = False

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
    def corners(self) -> Generator[Pos, None, None]:
        # 按照顺时针方向返回4个角
        yield (self.left, self.top)
        yield (self.right, self.top)
        yield (self.right, self.bottom)
        yield (self.left, self.bottom)

    def offset(self, hoffset: int, voffset: int) -> "Region":
        self.x += hoffset
        self.y += voffset
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


tree = Node(0, 0, 1920, 1080, 0)


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

    return _get_parent(tree, node) or tree


class CanvasButton(Region):
    def __init__(self, canvas, x, y, width, height, text):
        super().__init__(x, y, width, height)
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
    def on_press(self, event):
        pass

    @abstractmethod
    def on_release(self, event):
        pass


class MoveButton(CanvasButton):
    def __init__(self, canvas, x, y, width, height):
        super().__init__(canvas, x, y, width, height, "move")

    def on_press(self, event):
        runtime.moving = not runtime.moving
        if runtime.moving:
            self.canvas.itemconfig(self.rect, fill="yellow")  # 改变颜色以模拟按下效果

    def on_release(self, event):
        if not runtime.moving:
            self.canvas.itemconfig(self.rect, fill=self.origin_color)  # 恢复原始颜色


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


move_btn = MoveButton(runtime.canvas, 0, 0, 35, 20)


def on_click(event):
    mp.pos = int(runtime.canvas.canvasx(event.x)), int(runtime.canvas.canvasy(event.y))


def on_move(event):
    x, y = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)

    if runtime.moving:
        return

    global hint_box
    if hint_box:
        runtime.canvas.delete(hint_box)
    hint_box = runtime.canvas.create_rectangle(
        (*mp.pos, x, y), fill="", outline="yellow"
    )


def on_release(event):
    x, y = runtime.canvas.canvasx(event.x), runtime.canvas.canvasy(event.y)
    if mp.x == x and mp.y == y:
        return

    if runtime.moving:
        node = get_node((mp.x, mp.y), tree)
        logger.info(f"[TOUCHED]: {node}")
        if not node or node == runtime.root:
            logger.warning(f"Nothing To Move!")
            return
        hoffset, voffset = x - mp.x, y - mp.y
        parent = get_parent(node)
        r = node.get_region().offset(hoffset, voffset)
        for c in parent.children:
            if node == c:
                continue
            if detect_collision(r, c):
                logger.warning(f"Collision Detected: {r} vs {c} !")
                return
        OffsetVisitor(hoffset, voffset).visit(node)
        return

    global hint_box
    if hint_box:
        runtime.canvas.delete(hint_box)
        hint_box = None

    width, height = x - mp.x, y - mp.y
    tag_id = runtime.canvas.create_rectangle((*mp.pos, x, y), fill="", outline="black")
    node = Node(*mp.pos, width, height, tag_id)
    logger.info(f"[NEW]: {node}")

    if detect_collision(node, move_btn):
        runtime.canvas.delete(tag_id)
        return

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

        parent = node.parent
        label = f"{node.tag_id}"
        while parent:
            label = f"{parent.tag_id}" + CHILD_SEP + f"{label}"
            parent = parent.parent
            logger.info(f"parent: {parent}")

        node.title_id = runtime.canvas.create_text(
            node.x + NODE_LABEL_X_OFFSET,
            node.y + NODE_LABEL_Y_OFFSET,
            text=label,
            font=("Arial", 10, "bold"),
        )


class OffsetVisitor(DFSVisitor):
    def __init__(self, hoffset: int, voffset: int):
        self.hoffset = hoffset
        self.voffset = voffset

    def visit_node(self, node: Node):
        node.x += self.hoffset
        node.y += self.voffset
        runtime.canvas.coords(node.tag_id, node.left, node.top, node.right, node.bottom)
        LabelVisitor().visit_node(node)


runtime.canvas.bind("<Button-1>", on_click)
runtime.canvas.bind("<B1-Motion>", on_move)
runtime.canvas.bind("<B1-ButtonRelease>", on_release)


runtime.run()
