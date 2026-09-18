#!/usr/bin/env python3
"""Conservative comparison of diagram content and relationship metadata across all pages."""
import argparse
import json
import sys
from drawio_geom import read_pages, _style

# Whitelist presentation keys; unknown styles remain semantic by default.
COSMETIC = set('fillColor strokeColor fontColor fontFamily fontSize shadow arcSize opacity fillOpacity strokeOpacity strokeWidth align verticalAlign spacing spacingTop spacingBottom spacingLeft spacingRight labelBackgroundColor labelBorderColor edgeStyle elbow curved orthogonalLoop jettySize entryX entryY entryDx entryDy entryPerimeter exitX exitY exitDx exitDy exitPerimeter labelPosition verticalLabelPosition routingCenterX routingCenterY'.split())


def snapshot(path):
    pages=[]
    for pid,name,model in read_pages(path):
        cells={}
        parent_map={child:node for node in model.iter() for child in node}
        for cell in model.iter('mxCell'):
            attrs=dict(cell.attrib)
            wrapper=parent_map.get(cell)
            wrapper_attrs={}
            if wrapper is not None and wrapper.tag in ('object','UserObject'):
                wrapper_attrs=dict(wrapper.attrib)
                attrs['id']=wrapper.get('id',attrs.get('id',''))
            cid=attrs.pop('id',None)
            if cid is None: raise ValueError('cell missing ID')
            if cid in cells: raise ValueError('duplicate cell ID: '+cid)
            style=_style(attrs.pop('style',''))
            attrs['style']={k:v for k,v in style.items() if k not in COSMETIC}
            attrs['wrapper']=wrapper_attrs
            cells[cid]=attrs
        pages.append(dict(id=pid,name=name,cells=cells))
    return pages


def compare(before,after):
    a,b=snapshot(before),snapshot(after)
    changes=[]
    if len(a)!=len(b): changes.append('page count changed')
    for i,(x,y) in enumerate(zip(a,b),1):
        for key in ('id','name'):
            if x[key]!=y[key]: changes.append(f'page {i}: {key} changed')
        for cid in sorted(set(x['cells'])|set(y['cells'])):
            if x['cells'].get(cid)!=y['cells'].get(cid): changes.append(f'page {i}: cell {cid} content/relationship changed')
    return dict(unchanged=not changes,changes=changes,scope='Content, endpoints, ownership, unknown styles and wrapper metadata; excludes geometry. Review sequence timing/order and notation visually.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before'); ap.add_argument('after'); a=ap.parse_args()
    try: r=compare(a.before,a.after)
    except Exception as exc:
        print(json.dumps(dict(error=str(exc))));return 2
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r['unchanged'] else 1


if __name__=='__main__': sys.exit(main())
