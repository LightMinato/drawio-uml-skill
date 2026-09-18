"""Draw.io source model and supported rendered SVG geometry."""
from __future__ import annotations

import base64
import math
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# .drawio source
# --------------------------------------------------------------------------


def read_pages(path: str):
    root = ET.parse(path).getroot()
    if root.tag == "mxGraphModel":
        return [("page-1", "Page 1", root)]
    pages = []
    for index, diagram in enumerate(root.findall("diagram")):
        model = diagram.find("mxGraphModel")
        if model is None:
            body = (diagram.text or "").strip()
            if body.startswith("<"):
                model = ET.fromstring(body)
            else:
                model = ET.fromstring(urllib.parse.unquote(zlib.decompress(base64.b64decode(body), -15).decode()))
        if model.tag != "mxGraphModel":
            raise ValueError("page does not contain mxGraphModel")
        pages.append((diagram.get("id", str(index)), diagram.get("name", ""), model))
    if not pages:
        raise ValueError("no diagram pages")
    return pages


def read_page(path: str, page: int = 0) -> ET.Element:
    pages = read_pages(path)
    if page < 0 or page >= len(pages):
        raise ValueError(f"page index {page + 1} out of range (1..{len(pages)})")
    return pages[page][2]


def _style(style: str) -> dict:
    out = {}
    for part in (style or "").split(";"):
        if not part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


@dataclass
class Cell:
    id: str
    parent: str
    style: str
    value: str
    vertex: bool
    edge: bool
    source: str | None = None
    target: str | None = None
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    points: list = field(default_factory=list)
    offset: tuple | None = None

    @property
    def props(self) -> dict:
        return _style(self.style)

    @property
    def text(self) -> str:
        """Label as plain text (draw.io stores HTML with entities)."""
        t = re.sub(r"<br\s*/?>", " ", self.value or "")
        t = re.sub(r"<[^>]+>", "", t)
        return (t.replace("&nbsp;", " ").replace("&lt;", "<")
                 .replace("&gt;", ">").replace("&amp;", "&").replace("&#10;", " ").strip())

    @property
    def is_container(self) -> bool:
        p = self.props
        return ("swimlane" in self.style or p.get("shape") == "table"
                or self.id in ("0", "1"))


class Model:
    """Absolute geometry of every cell on one page."""

    def __init__(self, path: str, page: int = 0):
        root = read_page(path, page)
        self.page_w = float(root.get("pageWidth", 850))
        self.page_h = float(root.get("pageHeight", 1100))
        self.cells: dict[str, Cell] = {}
        layer = root.find("root")
        parent_map = {child: node for node in root.iter() for child in node}
        for c in (layer if layer is not None else root).iter("mxCell"):
            wrapper = parent_map.get(c)
            if wrapper is not None and wrapper.tag in ("object", "UserObject"):
                c = ET.fromstring(ET.tostring(c))
                c.set("id", wrapper.get("id", c.get("id", "")))
                c.set("value", wrapper.get("label", c.get("value", "")))
            cid = c.get("id")
            if cid is None:
                continue
            g = c.find("mxGeometry")
            cell = Cell(
                id=cid,
                parent=c.get("parent", "1"),
                style=c.get("style", "") or "",
                value=c.get("value", "") or "",
                vertex=c.get("vertex") == "1",
                edge=c.get("edge") == "1",
                source=c.get("source"),
                target=c.get("target"),
            )
            if g is not None:
                cell.x = float(g.get("x") or 0)
                cell.y = float(g.get("y") or 0)
                cell.w = float(g.get("width") or 0)
                cell.h = float(g.get("height") or 0)
                arr = g.find("Array")
                if arr is not None:
                    cell.points = [(float(p.get("x") or 0), float(p.get("y") or 0))
                                   for p in arr.findall("mxPoint")]
                off = g.find('mxPoint[@as="offset"]')
                if off is not None:
                    cell.offset = (float(off.get("x") or 0), float(off.get("y") or 0))
            if cid in self.cells:
                raise ValueError(f"duplicate cell ID: {cid}")
            self.cells[cid] = cell

        self.children: dict[str, list[str]] = {}
        for c in self.cells.values():
            self.children.setdefault(c.parent, []).append(c.id)

    # -- absolute geometry -------------------------------------------------
    def abs_xy(self, cell: Cell) -> tuple[float, float]:
        """Walk up the parent chain accumulating offsets (lane-local y fix)."""
        x, y, seen = cell.x, cell.y, {cell.id}
        p = self.cells.get(cell.parent)
        while p is not None and p.id not in seen:
            seen.add(p.id)
            x += p.x
            y += p.y
            p = self.cells.get(p.parent)
        return x, y

    def rect(self, cell_id: str) -> tuple[float, float, float, float] | None:
        c = self.cells.get(cell_id)
        if c is None or not c.vertex or c.is_container:
            return None
        x, y = self.abs_xy(c)
        if c.w <= 0 or c.h <= 0:
            return None
        return (x, y, c.w, c.h)

    def shapes(self, exclude_containers: bool = True) -> dict:
        """id -> (x, y, w, h) for every drawable vertex."""
        out = {}
        for c in self.cells.values():
            if not c.vertex or (exclude_containers and c.is_container):
                continue
            r = self.rect(c.id)
            if r:
                out[c.id] = r
        return out

    def edges(self) -> dict[str, Cell]:
        return {c.id: c for c in self.cells.values() if c.edge}

    def containers(self) -> list[str]:
        return [c.id for c in self.cells.values() if c.is_container and c.vertex]


# --------------------------------------------------------------------------
# exported SVG
# --------------------------------------------------------------------------

NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
ARGN = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4, "Z": 0}


def parse_path(d: str) -> list[tuple[float, float]]:
    """Parse a single subpath; sample Q/C curves, reject unsupported commands."""
    toks = re.findall(r"[a-zA-Z]|" + NUMBER, d)
    pts, cur, first, i, cmd = [], (0., 0.), None, 0, None
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]; i += 1
            if cmd.upper() not in ARGN:
                raise ValueError(f"unsupported SVG path command {cmd}")
            if cmd.upper() == 'Z':
                if first is not None and cur != first:
                    pts.append(first)
                cur = first
                cmd = None
                continue
        if cmd is None:
            raise ValueError("path has no active command")
        up, relative = cmd.upper(), cmd.islower()
        n = ARGN[up]
        vals = [float(v) for v in toks[i:i+n]]
        if len(vals) != n:
            raise ValueError("truncated SVG path")
        i += n
        def point(x, y):
            return (x + cur[0], y + cur[1]) if relative else (x, y)
        if up == 'H':
            dest = (vals[0] + (cur[0] if relative else 0), cur[1])
        elif up == 'V':
            dest = (cur[0], vals[0] + (cur[1] if relative else 0))
        else:
            dest = point(*vals[-2:])
        if up == 'M':
            if pts:
                raise ValueError("multiple SVG subpaths require manual geometry review")
            first = dest
            cmd = 'l' if relative else 'L'
        if up in ('Q', 'C'):
            controls = [cur] + [point(*vals[j:j+2]) for j in range(0,n,2)]
            for step in range(1,25):
                t = step / 24
                work = controls[:]
                while len(work) > 1:
                    work = [((1-t)*a[0]+t*b[0], (1-t)*a[1]+t*b[1]) for a,b in zip(work,work[1:])]
                pts.append(work[0])
        else:
            pts.append(dest)
        cur = dest
    return pts


def polyline_len(p):
    return sum(math.dist(a,b) for a,b in zip(p,p[1:]))


def simplify(p, tol=1e-8):
    out = []
    for point in p:
        if out and math.dist(out[-1], point) < tol:
            continue
        if len(out) >= 2 and abs(ccw(out[-2],out[-1],point)) < tol:
            a,b=out[-2:]
            if (b[0]-a[0])*(point[0]-b[0])+(b[1]-a[1])*(point[1]-b[1]) >= 0:
                out.pop()
        out.append(point)
    return out


def matrix_mul(a,b):
    return (a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5])


IDENTITY = (1,0,0,1,0,0)


def transform_matrix(text):
    result=IDENTITY
    rest=re.sub(r"([a-zA-Z]+)\s*\(([^)]*)\)", "", text).strip(' ,')
    if rest:
        raise ValueError(f"unsupported transform {text}")
    for name, body in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)",text):
        v=[float(x) for x in re.findall(NUMBER,body)]
        if name == 'translate' and len(v) in (1,2):
            m=(1,0,0,1,v[0],v[1] if len(v)==2 else 0)
        elif name == 'scale' and len(v) in (1,2):
            m=(v[0],0,0,v[-1],0,0)
        elif name == 'matrix' and len(v)==6:
            m=tuple(v)
        elif name == 'rotate' and len(v) in (1,3):
            angle=math.radians(v[0]); m=(math.cos(angle),math.sin(angle),-math.sin(angle),math.cos(angle),0,0)
            if len(v)==3:
                m=matrix_mul(matrix_mul((1,0,0,1,v[1],v[2]),m),(1,0,0,1,-v[1],-v[2]))
        else:
            raise ValueError(f"unsupported transform {name}")
        result=matrix_mul(result,m)
    return result


def apply_matrix(m,p):
    return (m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5])


def load_svg(path):
    """Read SVG with XML traversal; retain per-cell parse errors instead of hiding them."""
    root=ET.parse(path).getroot()
    if root.tag.split('}')[-1]!='svg':
        raise ValueError('render input is not an SVG')
    out={}
    def visit(el, inherited=IDENTITY, owner=None):
        tag=el.tag.split('}')[-1]
        if tag in ('defs','metadata'):
            return
        cid=el.get('data-cell-id',owner)
        if cid is not None:
            rec=out.setdefault(cid,dict(paths=[],rects=[],labels=[],outlines=[],errors=[],approximate=False))
        try:
            mat=matrix_mul(inherited,transform_matrix(el.get('transform','')))
        except ValueError as exc:
            if cid is None:
                raise
            rec['errors'].append(str(exc)); return
        if cid is not None:
            try:
                pts=None
                if tag=='path':
                    d=el.get('d','')
                    pts=parse_path(d)
                    rec['approximate'] |= bool(re.search('[QqCc]', d))
                elif tag in ('rect','ellipse','circle'):
                    if tag=='rect':
                        x,y,w,h=[float(el.get(k,0)) for k in ('x','y','width','height')]
                        pts=[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
                    else:
                        x,y=float(el.get('cx',0)),float(el.get('cy',0))
                        rx=float(el.get('rx',el.get('r',0))); ry=float(el.get('ry',el.get('r',0)))
                        pts=[(x+rx*math.cos(i*math.pi/32),y+ry*math.sin(i*math.pi/32)) for i in range(65)]
                        rec['approximate']=True
                    rec['outlines'].append([apply_matrix(mat,p) for p in pts]); pts=None
                elif tag in ('polygon','polyline'):
                    vals=[float(v) for v in re.findall(NUMBER,el.get('points',''))]
                    pts=list(zip(vals[::2],vals[1::2]))
                    if tag=='polygon' and pts: pts.append(pts[0])
                elif tag=='line':
                    pts=[(float(el.get('x1',0)),float(el.get('y1',0))),(float(el.get('x2',0)),float(el.get('y2',0)))]
                elif tag=='text':
                    text=''.join(el.itertext()); size=float(el.get('font-size',12))
                    x,y=float(el.get('x',0)),float(el.get('y',0))
                    w=_text_width(text,size)
                    if el.get('text-anchor')=='middle': x-=w/2
                    rec['labels'].append((x,y-size,w,size*1.3))
                    rec['approximate']=True
                if pts:
                    rec['paths'].append([apply_matrix(mat,p) for p in pts])
                if tag=='foreignObject':
                    # Browser HTML layout is not available in an XML parser.
                    rec['html_labels']=True
            except (ValueError,IndexError) as exc:
                rec['errors'].append(f'{tag}: {exc}')
        for child in el:
            visit(child,mat,cid)
    visit(root)
    return out


def _text_width(text,size):
    return sum(size*(1 if ord(ch)>0x2E80 else .55) for ch in text)


def shape_of(rec):
    outlines=list(rec.get('outlines',[]))
    for x,y,w,h in rec.get('rects',[]):
        outlines.append([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)])
    outlines += [p for p in rec.get('paths',[]) if len(p)>=4 and math.dist(p[0],p[-1])<1e-6]
    def area(p):
        return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:])))/2
    outlines=[p for p in outlines if area(p)>1]
    return ('poly',max(outlines,key=area)) if outlines else None


def edge_polyline(rec):
    paths=[p for p in rec.get('paths',[]) if len(p)>=2 and math.dist(p[0],p[-1])>1e-6]
    return simplify(max(paths,key=polyline_len)) if paths else None


# --------------------------------------------------------------------------
# geometry primitives
# --------------------------------------------------------------------------


def ccw(p, q, r):
    return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])


def seg_intersect(a, b, c, d) -> bool:
    """Proper intersection of segments ab and cd (touching endpoints excluded)."""
    d1, d2 = ccw(c, d, a), ccw(c, d, b)
    d3, d4 = ccw(a, b, c), ccw(a, b, d)
    return d1 * d2 < -1e-8 and d3 * d4 < -1e-8


def seg_dist(a, b, c, d) -> float:
    if seg_intersect(a, b, c, d):
        return 0.0
    def pt_seg(p, q, r):
        qx, qy = q[0] - p[0], q[1] - p[1]
        rx, ry = r[0] - p[0], r[1] - p[1]
        L = qx * qx + qy * qy
        if L == 0:
            return math.hypot(rx, ry)
        t = max(0.0, min(1.0, (rx * qx + ry * qy) / L))
        return math.hypot(rx - t * qx, ry - t * qy)
    return min(pt_seg(a, b, c), pt_seg(a, b, d), pt_seg(c, d, a), pt_seg(c, d, b))


def rect_edges(r):
    x, y, w, h = r
    c = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return list(zip(c, c[1:] + c[:1]))


def poly_edges(p):
    return list(zip(p, p[1:] + p[:1]))


def seg_shape_dist(a, b, shape) -> float:
    kind, geo = shape
    edges = rect_edges(geo) if kind == "rect" else poly_edges(geo)
    return min(seg_dist(a, b, c, d) for c, d in edges)


def seg_in_shape(a, b, shape) -> bool:
    kind, geo = shape
    edges = rect_edges(geo) if kind == "rect" else poly_edges(geo)
    return any(seg_intersect(a, b, c, d) for c, d in edges)


def point_in_shape(p, shape) -> bool:
    kind, geo = shape
    if kind == "rect":
        x, y, w, h = geo
        return x < p[0] < x + w and y < p[1] < y + h
    inside = False
    n = len(geo)
    for i in range(n):
        (x1, y1), (x2, y2) = geo[i], geo[(i + 1) % n]
        if (y1 > p[1]) != (y2 > p[1]):
            xin = x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1)
            if p[0] < xin:
                inside = not inside
    return inside


def shape_overlaps_rect(shape, rect) -> bool:
    """True only for a genuine overlap area (not a shared border)."""
    kind, geo = shape
    x, y, w, h = rect
    if kind == "rect":
        gx, gy, gw, gh = geo
        ox = min(gx + gw, x + w) - max(gx, x)
        oy = min(gy + gh, y + h) - max(gy, y)
        return ox > 2 and oy > 2
    pts = geo
    if any(x < p[0] < x + w and y < p[1] < y + h for p in pts):
        return True
    for a, b in rect_edges(rect):
        if seg_in_shape(a, b, shape):
            return True
    return False
