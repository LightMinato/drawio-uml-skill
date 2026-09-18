#!/usr/bin/env python3
"""Audit supported Draw.io SVG geometry. 0: checks clean; 1: defects; 2: incomplete."""
import argparse
import itertools
import json
import math
import sys
from drawio_geom import (Model, load_svg, shape_of, edge_polyline, seg_intersect,
                         seg_dist, point_in_shape, poly_edges, rect_edges)


def segments(points):
    return list(zip(points, points[1:]))


def boundary(shape):
    return rect_edges(shape[1]) if shape[0] == 'rect' else poly_edges(shape[1])


def inside(point, shape):
    # Boundary contact is not interior penetration.
    if any(seg_dist(point, point, a, b) < .05 for a, b in boundary(shape)):
        return False
    return point_in_shape(point, shape)


def pierces(a, b, shape):
    if inside(a, shape) or inside(b, shape):
        return True
    if inside(((a[0]+b[0])/2, (a[1]+b[1])/2), shape):
        return True
    return any(seg_intersect(a, b, c, d) for c, d in boundary(shape))


def shared_run(a, b, c, d):
    # Collinear overlap, including duplicate edges (separate from proper crossings).
    length = math.dist(a,b)
    if length < 1e-6:
        return False
    cross = lambda p: abs((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])) / length
    if cross(c) > .05 or cross(d) > .05:
        return False
    axis = 0 if abs(b[0]-a[0]) >= abs(b[1]-a[1]) else 1
    return min(max(a[axis],b[axis]),max(c[axis],d[axis])) - max(min(a[axis],b[axis]),min(c[axis],d[axis])) > 2


def audit(drawio, svg, page=1, gap=12, strict=False):
    if page < 1:
        raise ValueError('page must be 1 or greater')
    model = Model(drawio, page-1)
    rendered = load_svg(svg)
    report = dict(page=page, counts={}, errors=[], incomplete=[], warnings=[],
                  crossings=[], overlapping_routes=[], through_shape=[], node_overlap=[])
    for cid,c in model.edges().items():
        for endpoint in (c.source,c.target):
            if endpoint and endpoint not in model.cells:
                report['errors'].append(f'{cid}: dangling endpoint {endpoint}')
    def ancestors(cid):
        result=set()
        while cid in model.cells and cid not in result:
            result.add(cid); cid=model.cells[cid].parent
        return result
    def text_only(c):
        return 'text' in c.props or c.props.get('shape')=='text' or model.cells.get(c.parent, c).edge
    shape_ids = [cid for cid in model.shapes() if not text_only(model.cells[cid])]
    shapes,lines={},{}
    required=set(shape_ids) | set(model.edges())
    # Labels without dimensions still need to be present to avoid silent stale-page success.
    required |= {cid for cid,c in model.cells.items() if c.vertex and c.value and not c.is_container}
    if not shape_ids and not model.edges():
        report['incomplete'].append('source has no auditable shapes or connectors')
    for cid in sorted(required):
        rec=rendered.get(cid)
        if rec is None:
            report['incomplete'].append(f'{cid}: missing rendered cell'); continue
        report['incomplete'].extend(f'{cid}: {msg}' for msg in rec['errors'])
        if rec.get('approximate'):
            report['warnings'].append(f'{cid}: curved geometry or text measurements are approximate')
        if cid in shape_ids:
            shape=shape_of(rec)
            if shape: shapes[cid]=shape
            else: report['incomplete'].append(f'{cid}: no supported closed shape outline')
        if cid in model.edges():
            points=edge_polyline(rec)
            if points: lines[cid]=points
            else: report['incomplete'].append(f'{cid}: no supported connector path')
    if any(r.get('html_labels') for r in rendered.values()):
        report['warnings'].append('HTML label bounds are not measured; inspect label overlap, clipping and endpoint text visually')
    for (e1,p),(e2,q) in itertools.combinations(lines.items(),2):
        pairs=list(itertools.product(segments(p),segments(q)))
        if any(seg_intersect(a,b,c,d) for (a,b),(c,d) in pairs):
            report['crossings'].append([e1,e2])
        if any(shared_run(a,b,c,d) for (a,b),(c,d) in pairs):
            report['overlapping_routes'].append([e1,e2])
        # Skip proximity only near shared attachment; crossings above still checked.
        shared=(set(filter(None,(model.cells[e1].source,model.cells[e1].target))) &
                set(filter(None,(model.cells[e2].source,model.cells[e2].target))))
        if not shared and pairs:
            best=min(seg_dist(a,b,c,d) for (a,b),(c,d) in pairs)
            if 0 < best < gap:
                report['warnings'].append(f'{e1}/{e2}: connector spacing {best:.1f}px')
    for eid,points in lines.items():
        cell=model.cells[eid]
        owned=ancestors(cell.source)|ancestors(cell.target)
        for sid,shape in shapes.items():
            if sid in owned or cell.source in ancestors(sid) or cell.target in ancestors(sid):
                continue
            if any(pierces(a,b,shape) for a,b in segments(points)):
                report['through_shape'].append(dict(edge=eid,shape=sid))
    for (a,sa),(b,sb) in itertools.combinations(shapes.items(),2):
        if a in ancestors(b) or b in ancestors(a): continue
        points_a=[p for p,q in boundary(sa)]; points_b=[p for p,q in boundary(sb)]
        center_a=tuple(sum(p[i] for p in points_a)/len(points_a) for i in (0,1))
        center_b=tuple(sum(p[i] for p in points_b)/len(points_b) for i in (0,1))
        if (any(inside(p,sb) for p in points_a+[center_a]) or any(inside(p,sa) for p in points_b+[center_b]) or
            any(seg_intersect(p,q,r,s) for p,q in boundary(sa) for r,s in boundary(sb))):
            report['node_overlap'].append([a,b])
    report['counts']=dict(source_shapes=len(shape_ids),measured_shapes=len(shapes),source_connectors=len(model.edges()),measured_connectors=len(lines))
    hard=bool(report['errors'] or report['through_shape'] or report['node_overlap'])
    if strict:
        hard |= bool(report['crossings'] or report['overlapping_routes'] or
                     any('spacing' in w for w in report['warnings']))
    report['status']='INCOMPLETE' if report['incomplete'] else 'FAIL' if hard else 'CHECKS_PASSED'
    report['exit_code']=2 if report['incomplete'] else 1 if hard else 0
    report['scope']='Supported geometry only; UML semantics and HTML typography require review.'
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('drawio'); ap.add_argument('svg')
    ap.add_argument('--page',type=int,default=1)
    ap.add_argument('--gap',type=float,default=12)
    ap.add_argument('--strict',action='store_true')
    ap.add_argument('--json',action='store_true')
    a=ap.parse_args()
    try:
        r=audit(a.drawio,a.svg,a.page,a.gap,a.strict)
    except Exception as exc:
        r=dict(status='INCOMPLETE',exit_code=2,error=str(exc))
    if a.json: print(json.dumps(r,ensure_ascii=False,indent=2))
    else:
        print(r['status'])
        for key,value in r.items():
            if value and key not in ('status','exit_code'): print(f'{key}: {value}')
    return r['exit_code']


if __name__=='__main__':
    sys.exit(main())
