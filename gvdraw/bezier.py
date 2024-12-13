def cubic_bezier_points(canvas, points, steps=100):
    def cubic_bezier(p0, p1, p2, p3, t):
        """计算一个三次 Bézier 曲线上的一点"""
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        return (x, y)

    bezier_points = []
    for i in range(len(points)-3):
        for j in range(steps+1):
            t = j / steps
            bezier_points.append(cubic_bezier(points[i], points[i+1], points[i+2], points[i+3], t))

    # 处理最后三点到终点
    last_three = points[-3:]
    for j in range(steps+1):
        t = j / steps
        bezier_points.append(cubic_bezier(last_three[0], last_three[1], last_three[2], last_three[2], t))
    canvas.create_line(
        [coord for point in bezier_points for coord in point],
        fill="black",
        width=1,
        smooth=True,
    )

    return bezier_points
