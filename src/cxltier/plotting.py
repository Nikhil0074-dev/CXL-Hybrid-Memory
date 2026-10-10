"""Dependency-free SVG charts."""
from __future__ import annotations

from typing import Dict, List, Sequence
from xml.sax.saxutils import escape

PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#9c755f", "#bab0ac", "#ff9da7"]


def grouped_bar_svg(title: str, groups: Sequence[str], series: Dict[str, Sequence[float]],
                    ylabel: str = "speedup vs static_firsttouch", ref_line: float = 1.0) -> str:
    names = list(series)
    if not groups or not names:
        raise ValueError("need at least one group and one series")
    for nm in names:
        if len(series[nm]) != len(groups):
            raise ValueError(f"series {nm} has wrong length")
    W = max(900, 120 * len(groups) + 200)
    H = 460
    ml, mr, mt, mb = 70, 20, 50, 120
    pw, ph = W - ml - mr, H - mt - mb
    vals = [v for nm in names for v in series[nm] if v == v]
    vmax = max(vals + [ref_line]) * 1.1
    gw = pw / len(groups)
    bw = gw * 0.85 / len(names)

    def y(v: float) -> float:
        return mt + ph - (v / vmax) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{W/2}" y="24" text-anchor="middle" font-size="15" font-weight="bold">{escape(title)}</text>']
    for i in range(6):
        v = vmax * i / 5
        o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e0e0e0"/>')
        o.append(f'<text x="{ml-6}" y="{y(v)+4:.1f}" text-anchor="end">{v:.2f}</text>')
    o.append(f'<text x="14" y="{mt+ph/2}" transform="rotate(-90 14 {mt+ph/2})" text-anchor="middle">{escape(ylabel)}</text>')
    o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(ref_line):.1f}" y2="{y(ref_line):.1f}" stroke="#333" stroke-dasharray="4 3"/>')
    for gi, g in enumerate(groups):
        x0 = ml + gi * gw + gw * 0.075
        for si, nm in enumerate(names):
            v = series[nm][gi]
            if v != v:
                continue
            o.append(f'<rect x="{x0+si*bw:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{mt+ph-y(v):.1f}" fill="{PALETTE[si%len(PALETTE)]}"/>')
        o.append(f'<text x="{ml+gi*gw+gw/2:.1f}" y="{mt+ph+16}" text-anchor="middle">{escape(g)}</text>')
    lx, ly = ml, H - 70
    for si, nm in enumerate(names):
        cx = lx + (si % 5) * 170
        cy = ly + (si // 5) * 18
        o.append(f'<rect x="{cx}" y="{cy}" width="12" height="12" fill="{PALETTE[si%len(PALETTE)]}"/>')
        o.append(f'<text x="{cx+17}" y="{cy+10}">{escape(nm)}</text>')
    o.append("</svg>")
    return "\n".join(o)


def line_svg(title: str, series: Dict[str, Sequence[float]], ylabel: str, xlabel: str = "epoch") -> str:
    names = list(series)
    if not names:
        raise ValueError("need at least one series")
    n = max(len(series[nm]) for nm in names)
    W, H = 900, 420
    ml, mr, mt, mb = 70, 20, 50, 90
    pw, ph = W - ml - mr, H - mt - mb
    vals = [v for nm in names for v in series[nm]]
    vmax = max(vals) * 1.05 or 1.0
    vmin = 0.0

    def x(i: int) -> float:
        return ml + (pw * i / (n - 1) if n > 1 else pw / 2)

    def y(v: float) -> float:
        return mt + ph - ((v - vmin) / (vmax - vmin)) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{W/2}" y="24" text-anchor="middle" font-size="15" font-weight="bold">{escape(title)}</text>']
    for i in range(6):
        v = vmax * i / 5
        o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e0e0e0"/>')
        o.append(f'<text x="{ml-6}" y="{y(v)+4:.1f}" text-anchor="end">{v:.3g}</text>')
    o.append(f'<text x="14" y="{mt+ph/2}" transform="rotate(-90 14 {mt+ph/2})" text-anchor="middle">{escape(ylabel)}</text>')
    o.append(f'<text x="{ml+pw/2}" y="{mt+ph+30}" text-anchor="middle">{escape(xlabel)}</text>')
    for si, nm in enumerate(names):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(series[nm]))
        o.append(f'<polyline fill="none" stroke="{PALETTE[si%len(PALETTE)]}" stroke-width="2" points="{pts}"/>')
        cx = ml + (si % 4) * 200
        cy = H - 40 + (si // 4) * 16
        o.append(f'<rect x="{cx}" y="{cy}" width="12" height="12" fill="{PALETTE[si%len(PALETTE)]}"/>')
        o.append(f'<text x="{cx+17}" y="{cy+10}">{escape(nm)}</text>')
    o.append("</svg>")
    return "\n".join(o)
