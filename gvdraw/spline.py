import tkinter as tk
import numpy as np
from typing import Tuple, List

Pos = Tuple[int, int]


def catmull_rom_spline(points, steps=50):
    """
    计算并返回给定点之间的 Catmull-Rom 样条上的点。

    :param points: 点列表 [(x1, y1), (x2, y2), ...]
    :param steps: 每段样条的细分步数
    :return: 平滑曲线上的点列表
    """

    def point_on_segment(p0, p1, p2, p3, t):
        """计算一个 Catmull-Rom 样条上的一点"""
        t2 = t * t
        t3 = t2 * t
        return (
            0.5
            * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            ),
            0.5
            * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            ),
        )

    if len(points) < 4:
        raise ValueError("需要至少 4 个点来创建 Catmull-Rom 样条")

    # 复制第一个和最后一个点以闭合曲线（可选）
    extended_points = [points[0]] + points + [points[-1]]

    spline_points = []
    for i in range(1, len(extended_points) - 2):
        for j in range(steps + 1):
            t = j / steps
            spline_points.append(
                point_on_segment(
                    extended_points[i - 1],
                    extended_points[i],
                    extended_points[i + 1],
                    extended_points[i + 2],
                    t,
                )
            )

    return spline_points


def draw_smooth_curve(canvas, points: List[Pos], color="black", width=1):
    
    """
    在 Canvas 上绘制平滑曲线。

    :param canvas: Tkinter Canvas 对象
    :param points: 点列表 [(x1, y1), (x2, y2), ...]
    :param color: 曲线颜色
    :param width: 曲线宽度
    """
    if len(points) < 4:
        # 如果点少于4个，则直接连线
        if len(points) >= 2:
            canvas.create_line(
                [coord for point in points for coord in point],
                fill=color,
                width=width,
                smooth=True,
            )
        return

    spline_points = catmull_rom_spline(points)
    if spline_points:
        canvas.create_line(
            [coord for point in spline_points for coord in point],
            fill=color,
            width=width,
            smooth=True,
        )
