import logging
import tkinter as tk

logger = logging.getLogger(__name__)

import tkinter as tk

root = tk.Tk()
canvas = tk.Canvas(root)

class Node:
    
    def __init__(self, parent, x: int, y: int, width: int, height: int, label: str) -> None:
        self.x, self.y, self.width, self.height = x, y, width, height
        self.parent = parent
        self.label = label
        
        # 绘制按钮
        self.button  = canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height, 
            fill="lightblue", outline="blue", width=2
        )
        self.label = canvas.create_text(
            self.x + self.width // 2, self.y + self.height // 2,
            text=self.label, font=("Arial", 12)
        )
        
        # 绑定按钮点击事件
        canvas.tag_bind(self.button, "<Button-1>", self.on_click)

        # 可调整大小的区域
        self.widget = canvas.create_rectangle(
            self.x + self.width - 10, self.y + self.height - 10, 
            self.x + self.width, self.y + self.height, 
            fill="red", outline="black", width=1, tags="resize"
        )
        canvas.tag_bind("resize", "<B1-Motion>", self.on_resize)

    def on_click(self):
        pass
        
    def on_resize(self, event):
        # 获取鼠标位置
        new_width = event.x - self.x
        new_height = event.y - self.y
        
        # 更新按钮的大小
        if new_width > 50 and new_height > 30:  # 限制最小大小
            self.width = new_width
            self.height = new_height
            canvas.coords(self.widget, self.x, self.y, self.x + self.width, self.y + self.height)
            canvas.coords(self.label, self.x + self.width // 2, self.y + self.height // 2)
            canvas.coords("resize", self.x + self.width - 10, self.y + self.height - 10, 
                               self.x + self.width, self.y + self.height)


def on_button_click():
    print("Button clicked!")


if __name__ == "__main__":
    node = Node(root, 50, 50, 100, 50, "Start")
    root.title("Resizable Button Example")
    canvas.pack()
    root.mainloop()
    
    
