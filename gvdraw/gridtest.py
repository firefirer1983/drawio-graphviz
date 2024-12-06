import tkinter as tk

root = tk.Tk()

# 创建一个主框架
mainframe = tk.Frame(root)
mainframe.grid(column=0, row=0, sticky="nwes")

# 配置行和列的行为
root.grid_columnconfigure(0, weight=1)  # 使第0列可以伸缩
root.grid_rowconfigure(0, weight=1)  # 使第0行可以伸缩

# 添加一些控件到mainframe
label = tk.Label(mainframe, text="Hello, Tkinter!")
label.grid(column=0, row=0)

button = tk.Button(mainframe, text="Click me!")
button.grid(column=1, row=0)

root.mainloop()
