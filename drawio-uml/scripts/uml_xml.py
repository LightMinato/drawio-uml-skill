"""Small explicit-layout Draw.io XML builder; no external dependencies."""
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

RELATIONS = {
    'association': 'startArrow=none;endArrow=none;',
    'directed-association': 'startArrow=none;endArrow=open;endFill=0;',
    'generalization': 'startArrow=none;endArrow=block;endFill=0;',
    'realization': 'startArrow=none;endArrow=block;endFill=0;dashed=1;',
    'dependency': 'startArrow=none;endArrow=open;endFill=0;dashed=1;',
    'aggregation': 'startArrow=diamond;startFill=0;endArrow=none;',
    'composition': 'startArrow=diamond;startFill=1;endArrow=none;',
    'call': 'startArrow=none;endArrow=block;endFill=1;',
    'async': 'startArrow=none;endArrow=open;endFill=0;',
    'reply': 'startArrow=none;endArrow=open;endFill=0;dashed=1;',
}
NODE = 'whiteSpace=wrap;html=1;rounded=0;fillColor=#FFFFFF;strokeColor=#64748B;fontColor=#172033;fontSize=15;fontFamily=Helvetica;spacing=10;'
EDGE = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#475569;fontColor=#334155;fontSize=13;labelBackgroundColor=#FFFFFF;'


class Diagram:
    def __init__(self, name='UML', width=1200, height=900, page_id='uml-page'):
        self.doc = ET.Element('mxfile', host='drawio-uml')
        page = ET.SubElement(self.doc, 'diagram', id=page_id, name=name)
        model = ET.SubElement(page, 'mxGraphModel', grid='1', gridSize='10', page='1',
                              pageWidth=str(width), pageHeight=str(height))
        self.root = ET.SubElement(model, 'root')
        ET.SubElement(self.root, 'mxCell', id='0')
        ET.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.ids = {'0', '1'}

    def cell(self, cid, **attrs):
        if cid in self.ids:
            raise ValueError(f'duplicate cell ID: {cid}')
        self.ids.add(cid)
        return ET.SubElement(self.root, 'mxCell', id=cid, **attrs)

    def node(self, cid, text, x, y, w=220, h=100, style='', parent='1'):
        c = self.cell(cid, value=text, style=NODE + style, vertex='1', parent=parent)
        ET.SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
        return c

    def class_box(self, cid, name, attributes, operations, x, y, w=240, h=150, stereotype=''):
        title = (escape('«' + stereotype + '»') + '<br/>' if stereotype else '') + '<b>' + escape(name) + '</b>'
        rows = [f'<tr><td style="text-align:center;padding:6px;">{title}</td></tr>']
        for members in (attributes, operations):
            text = '<br/>'.join(escape(t) for t in members) or '&#160;'
            rows.append(f'<tr><td style="border-top:1px solid #94A3B8;text-align:left;padding:6px;">{text}</td></tr>')
        label = '<table style="border-collapse:collapse;width:100%;">' + ''.join(rows) + '</table>'
        return self.node(cid, label, x, y, w, h, 'spacing=0;fillColor=' + ('#EFF6FF;' if stereotype == 'interface' else '#FFFFFF;'))

    def edge(self, cid, source, target, kind='association', label='', points=(), style='', start=None, end=None):
        attrs = dict(value=label, style=EDGE + RELATIONS[kind] + style, edge='1', parent='1')
        for key, value in [('source', source), ('target', target)]:
            if value is not None:
                if value not in self.ids:
                    raise ValueError(f'unknown {key}: {value}')
                attrs[key] = value
        c = self.cell(cid, **attrs)
        g = ET.SubElement(c, 'mxGeometry', relative='1', **{'as': 'geometry'})
        if points:
            arr = ET.SubElement(g, 'Array', **{'as': 'points'})
            for x, y in points:
                ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))
        for key, point in [('sourcePoint', start), ('targetPoint', end)]:
            if point is not None:
                ET.SubElement(g, 'mxPoint', x=str(point[0]), y=str(point[1]), **{'as': key})
        return c

    def endpoint_label(self, cid, edge, text, at='target', offset=(0, -14)):
        if edge not in self.ids or at not in ('source', 'target'):
            raise ValueError('edge must exist and at must be source or target')
        c = self.cell(cid, value=text, style='text;html=1;align=center;verticalAlign=middle;fontSize=13;labelBackgroundColor=#FFFFFF;', vertex='1', parent=edge, connectable='0')
        g = ET.SubElement(c, 'mxGeometry', x='-0.8' if at == 'source' else '0.8', y='0', relative='1', **{'as': 'geometry'})
        ET.SubElement(g, 'mxPoint', x=str(offset[0]), y=str(offset[1]), **{'as': 'offset'})

    def write(self, path):
        ET.indent(self.doc)
        Path(path).write_text(ET.tostring(self.doc, encoding='unicode'), encoding='utf-8')
