#!/usr/bin/env python3
from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FONT = next(path for path in [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")] if path.exists())

NAVY, DARK = "#173B63", "#16202A"
BLUE, GRAY, ORANGE = "#DCEBFA", "#EEF1F4", "#FCE6CF"
GREEN, PURPLE, RED = "#DDF1E5", "#EAE1F7", "#F8DADA"


def fnt(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(str(FONT), size=size, index=1 if bold else 0)
    except OSError:
        return ImageFont.truetype(str(FONT), size=size)


def wrap(draw, text, font, width):
    result, line = [], ""
    for char in text:
        trial = line + char
        if not line or draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            result.append(line)
            line = char
    if line:
        result.append(line)
    return result


def box(draw, xy, text, fill, size=30, bold=True):
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=NAVY, width=4)
    font = fnt(size, bold)
    x1, y1, x2, y2 = xy
    lines = []
    for item in text.split("\n"):
        lines.extend(wrap(draw, item, font, x2 - x1 - 28))
    heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    y = y1 + ((y2 - y1) - sum(heights) - 7 * (len(lines) - 1)) / 2
    for line, height in zip(lines, heights):
        width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((x1 + x2 - width) / 2, y), line, font=font, fill=DARK)
        y += height + 7


def arrow(draw, start, end):
    draw.line([start, end], fill=NAVY, width=6)
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    draw.polygon([
        end,
        (x2 - ux * 22 + px * 10, y2 - uy * 22 + py * 10),
        (x2 - ux * 22 - px * 10, y2 - uy * 22 - py * 10),
    ], fill=NAVY)


def heading(draw, title, subtitle):
    draw.text((75, 45), title, font=fnt(50, True), fill=NAVY)
    draw.text((75, 112), subtitle, font=fnt(28), fill="#51606F")


def save(name, paint):
    image = Image.new("RGB", (2400, 1400), "white")
    draw = ImageDraw.Draw(image)
    paint(draw)
    image.save(OUT / f"{name}.png", dpi=(200, 200))
    image.save(OUT / f"{name}.pdf", resolution=200.0)


def model(draw):
    heading(draw, "轨迹输运脉冲视频取证：CCF-A 候选主结构", "把生成异常与传播退化分开建模，膜状态沿物体运动轨迹传播")
    box(draw, (65, 275, 350, 535), "观测视频\nRGB・时间戳\n有效画面掩码\n编码元信息", BLUE, 28)
    box(draw, (450, 205, 760, 445), "运动/特征对应\nWarp 算子 W(t)\n相机运动补偿", GRAY, 28)
    box(draw, (855, 185, 1185, 465), "多尺度有符号残差\nRGB・边缘・二阶\n小波・Patch 轨迹", ORANGE, 28)
    box(draw, (1280, 205, 1610, 445), "局部尺度归一化事件\nR / sigma_hat\n自适应触发阈值", GREEN, 28)
    box(draw, (1705, 180, 2035, 470), "轨迹输运 LIF\nWarp(V(t-1), W(t))\n有界 leak 与 threshold", PURPLE, 27)
    box(draw, (2140, 285, 2340, 545), "视频级输出\n真伪分数\n时间证据\n空间 Tube 证据", BLUE, 27)
    box(draw, (450, 760, 760, 1010), "退化质量编码\n噪声・编码・缩放\n帧率・平台属性", GRAY, 28)
    box(draw, (855, 760, 1185, 1010), "Nuisance 表征\n预测退化类型/强度", ORANGE, 29)
    box(draw, (1280, 760, 1610, 1010), "取证/退化解耦\n正交约束或 GRL\n同源跨退化一致性", GREEN, 27)
    box(draw, (1705, 760, 2035, 1010), "时空 Tube 证据\n物体/运动边缘\n排除 Padding 外圈", RED, 28)
    arrow(draw, (350, 380), (450, 325)); arrow(draw, (760, 325), (855, 325))
    arrow(draw, (1185, 325), (1280, 325)); arrow(draw, (1610, 325), (1705, 325))
    arrow(draw, (2035, 325), (2140, 410)); arrow(draw, (350, 455), (450, 885))
    arrow(draw, (760, 885), (855, 885)); arrow(draw, (1185, 885), (1280, 885))
    arrow(draw, (1610, 885), (1705, 430)); arrow(draw, (1870, 470), (1870, 760))
    arrow(draw, (2035, 885), (2240, 545))
    draw.text((105, 1130), "训练：同一源视频的 clean + 多种 degraded counterfactual；测试：仅输入单个未知视频", font=fnt(31, True), fill=NAVY)
    draw.text((105, 1200), "对照：固定像素 LIF｜可学习 LIF｜参数匹配 ANN｜普通增强｜WaveRep｜无 Tube｜随机区域", font=fnt(29), fill=DARK)
    draw.text((105, 1265), "判据：未知生成器 × 未见传播路径；全链路计入 Warp、骨干、残差与 SNN 开销", font=fnt(29), fill=DARK)


def milestones(draw):
    heading(draw, "CCF-A 研究路线：先证明机制，再扩展模型与数据", "RoboVid v02 用于 pilot；公共基准与 v03 承担主结果")
    xs = [65, 450, 835, 1220, 1605, 1990]
    texts = [
        "G0 旧资产清算\nv02 协议审计\n历史结果降级\nGate：无 test 训练",
        "G1 机制原型\n运动对齐\n尺度归一化事件\nGate：减少伪脉冲",
        "G2 主结构\n轨迹输运 LIF\nTube 证据\nGate：超过匹配 ANN",
        "G3 解耦学习\n跨退化同源一致性\nNuisance 分离\nGate：未见路径改善",
        "G4 双重泛化\nv03 + 公共基准\n未知生成器 × 未知路径\nGate：最差组稳定",
        "G5 论文证据包\n独立重算・理论边界\n代码・数据卡・失败例\nGate：主张可追溯",
    ]
    for x, fill, text in zip(xs, [GRAY, ORANGE, PURPLE, GREEN, BLUE, "#FFF0CC"], texts):
        box(draw, (x, 295, x + 315, 690), text, fill, 27)
    for x in xs[:-1]:
        arrow(draw, (x + 315, 493), (x + 385, 493))
    box(draw, (345, 835, 2055, 1095), "论文主张\n① 传播退化制造 nuisance spike　② 归一化事件控制误触发\n③ 轨迹输运膜状态保留结构化生成异常\n④ 双重留出验证泛化", "#E8F2FF", 32)
    draw.text((225, 1200), "No-Go：机制无效则停止 SNN；ANN 更强则转向通用轨迹输运；仅 RoboVid 有效则不投稿 CCF-A 主会", font=fnt(29, True), fill="#8B2C2C")


def write_drawio(name, nodes, edges):
    mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="Codex", version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id=name, name="Page-1")
    model = ET.SubElement(diagram, "mxGraphModel", dx="2400", dy="1400", grid="1", gridSize="10", page="1", pageWidth="2400", pageHeight="1400")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0"); ET.SubElement(root, "mxCell", id="1", parent="0")
    for node_id, label, x, y, width, height, fill, size in nodes:
        style = f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={NAVY};strokeWidth=4;fontSize={size};fontStyle=1;align=center;verticalAlign=middle;"
        cell = ET.SubElement(root, "mxCell", id=node_id, value=html.escape(label), style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(width), height=str(height), **{"as": "geometry"})
    for idx, (source, target) in enumerate(edges):
        style = f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor={NAVY};strokeWidth=5;"
        edge = ET.SubElement(root, "mxCell", id=f"e{idx}", style=style, edge="1", parent="1", source=source, target=target)
        ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
    ET.ElementTree(mxfile).write(OUT / f"{name}.drawio", encoding="utf-8", xml_declaration=True)


save("ccfa-model", model)
save("ccfa-milestones", milestones)

write_drawio("ccfa-model", [
    ("c1", "观测视频", 65,275,285,260,BLUE,30), ("c2", "运动/特征对应",450,205,310,240,GRAY,30),
    ("c3", "多尺度有符号残差",855,185,330,280,ORANGE,29), ("c4", "局部尺度归一化事件",1280,205,330,240,GREEN,29),
    ("c5", "轨迹输运 LIF",1705,180,330,290,PURPLE,30), ("c6", "视频级取证输出",2140,285,200,260,BLUE,28),
    ("c7", "退化质量编码",450,760,310,250,GRAY,29), ("c8", "Nuisance 表征",855,760,330,250,ORANGE,29),
    ("c9", "取证/退化解耦",1280,760,330,250,GREEN,29), ("c10", "时空 Tube 证据",1705,760,330,250,RED,29)
], [("c1","c2"),("c2","c3"),("c3","c4"),("c4","c5"),("c5","c6"),("c1","c7"),("c7","c8"),("c8","c9"),("c9","c5"),("c5","c10"),("c10","c6")])

write_drawio("ccfa-milestones", [
    (f"g{i}", label, x,295,315,395,fill,28)
    for i, (x, fill, label) in enumerate(zip(
        [65,450,835,1220,1605,1990], [GRAY,ORANGE,PURPLE,GREEN,BLUE,"#FFF0CC"],
        ["G0 旧资产清算","G1 机制原型","G2 主结构","G3 解耦学习","G4 双重泛化","G5 论文证据包"]
    ))
], [(f"g{i}", f"g{i+1}") for i in range(5)])

print(OUT)
