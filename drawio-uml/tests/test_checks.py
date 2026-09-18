import base64
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
from uml_xml import Diagram
from drawio_geom import parse_path,shape_of,read_pages,Model,load_svg,seg_dist
from verify import audit
from compare_semantics import compare
from export_diagram import export


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def source(self,edges=True):
        d=Diagram()
        d.node('a','A',0,0,50,50)
        d.node('b','B',200,0,50,50)
        if edges: d.edge('e','a','b')
        p=self.root/'source.drawio';d.write(p)
        return p

    def svg(self,body):
        p=self.root/'render.svg';p.write_text('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>')
        return p

    def rect(self,cid,x,y,w=50,h=50):
        return f'<g data-cell-id="{cid}"><rect height="{h}" width="{w}" y="{y}" x="{x}"/></g>'

    def path(self,cid,d):
        return f'<g data-cell-id="{cid}"><path d="{d}"/></g>'

    def test_empty_render_is_incomplete(self):
        r=audit(self.source(),self.svg(''))
        self.assertEqual(r['exit_code'],2)
        self.assertIn('a: missing rendered cell',r['incomplete'])

    def test_missing_connector_is_incomplete(self):
        r=audit(self.source(),self.svg(self.rect('a',0,0)+self.rect('b',200,0)))
        self.assertEqual(r['exit_code'],2)

    def test_closed_diamond_is_measured(self):
        pts=parse_path('M 50 0 L 100 50 L 50 100 L 0 50 Z')
        self.assertEqual(pts[0],pts[-1])
        self.assertIsNotNone(shape_of({'paths':[pts]}))

    def test_relative_paths_and_scientific_notation(self):
        self.assertEqual(parse_path('M 1e2 100 l 50 0 h 20 v -30'),[(100,100),(150,100),(170,100),(170,70)])

    def test_curves_sampled(self):
        pts=parse_path('M 0 0 Q 50 100 100 0')
        self.assertGreater(max(y for x,y in pts),49)
        self.assertEqual(pts[-1],(100,0))

    def test_unsupported_path_is_disclosed(self):
        r=audit(self.source(),self.svg(self.rect('a',0,0)+self.rect('b',200,0)+self.path('e','M 50 25 A 30 20 0 0 0 200 25')))
        self.assertEqual(r['exit_code'],2)
        self.assertTrue(any('unsupported' in x for x in r['incomplete']))

    def test_transform_and_attribute_order(self):
        p=self.svg('<g transform="translate(100,20) scale(2)">'+self.rect('a',0,0)+'</g>')
        shape=shape_of(load_svg(p)['a'])
        self.assertIn((200,120),shape[1])

    def test_source_bare_and_compressed(self):
        full=self.source();model=ET.parse(full).getroot().find('diagram/mxGraphModel')
        bare=self.root/'bare.drawio';bare.write_text(ET.tostring(model,encoding='unicode'))
        self.assertEqual(len(Model(str(bare)).cells),5)
        raw=urllib.parse.quote(ET.tostring(model,encoding='unicode')).encode()
        compressor=zlib.compressobj(wbits=-15)
        text=base64.b64encode(compressor.compress(raw)+compressor.flush()).decode()
        compressed=self.root/'compressed.drawio';compressed.write_text('<mxfile><diagram>'+text+'</diagram></mxfile>')
        self.assertEqual(len(Model(str(compressed)).cells),5)

    def test_wrapped_object(self):
        p=self.root/'wrapped.drawio'
        p.write_text('<mxGraphModel><root><object id="a" label="A"><mxCell vertex="1" parent="1"><mxGeometry width="100" height="50"/></mxCell></object></root></mxGraphModel>')
        self.assertEqual(Model(str(p)).cells['a'].value,'A')

    def test_shared_source_crossing_not_exempt(self):
        d=Diagram();d.node('a','A',0,0,50,50);d.node('b','B',200,0,50,50);d.node('c','C',200,200,50,50)
        d.edge('e1','a','b');d.edge('e2','a','c');p=self.root/'fan.drawio';d.write(p)
        svg=self.svg(self.rect('a',0,0)+self.rect('b',200,0)+self.rect('c',200,200)+self.path('e1','M 50 25 L 160 25 L 160 180 L 225 180 L 225 50')+self.path('e2','M 25 50 L 25 100 L 250 100 L 250 225'))
        r=audit(p,svg)
        self.assertEqual(r['crossings'],[['e1','e2']])

    def test_through_unrelated_shape(self):
        d=Diagram()
        for cid,x in [('a',0),('b',200),('c',100)]: d.node(cid,cid,x,0,50,50)
        d.edge('e','a','b');p=self.root/'pierce.drawio';d.write(p)
        r=audit(p,self.svg(''.join(self.rect(cid,x,0) for cid,x in [('a',0),('b',200),('c',100)])+self.path('e','M 50 25 L 200 25')))
        self.assertEqual(r['through_shape'],[{'edge':'e','shape':'c'}]);self.assertEqual(r['exit_code'],1)

    def test_unrelated_overlapping_nodes(self):
        r=audit(self.source(False),self.svg(self.rect('a',0,0)+self.rect('b',20,20)))
        self.assertEqual(r['node_overlap'],[['a','b']]);self.assertEqual(r['exit_code'],1)

    def test_touching_shapes_are_not_overlap(self):
        r=audit(self.source(False),self.svg(self.rect('a',0,0)+self.rect('b',50,0)))
        self.assertEqual(r['node_overlap'],[])

    def test_valid_render(self):
        r=audit(self.source(),self.svg(self.rect('a',0,0)+self.rect('b',200,0)+self.path('e','M 50 25 L 200 25')))
        self.assertEqual(r['exit_code'],0)

    def test_multiway_diamond_has_no_binary_rule(self):
        d=Diagram();d.node('choice','[condition]',0,0,100,100,'rhombus;');p=self.root/'decision.drawio';d.write(p)
        r=audit(p,self.svg(self.path('choice','M 50 0 L 100 50 L 50 100 L 0 50 Z')))
        self.assertEqual(r['exit_code'],0)

    def test_crossing_segment_distance_is_zero(self):
        self.assertEqual(seg_dist((0,0),(100,0),(50,-50),(50,50)),0)

    def test_semantics_geometry_allowed_relation_change_detected(self):
        before=self.source();after=self.root/'after.drawio';root=ET.parse(before)
        root.find('.//mxGeometry').set('x','999');root.write(after)
        self.assertTrue(compare(before,after)['unchanged'])
        root.find('.//mxCell[@id="e"]').set('style','endArrow=block;endFill=0;');root.write(after)
        self.assertFalse(compare(before,after)['unchanged'])

    def test_semantics_italic_change_detected(self):
        before=self.source();after=self.root/'after.drawio';root=ET.parse(before)
        root.find('.//mxCell[@id="a"]').set('style','fontStyle=2;');root.write(after)
        self.assertFalse(compare(before,after)['unchanged'])

    def test_page_range(self):
        with self.assertRaises(ValueError): audit(self.source(),self.svg(''),page=2)

    def test_cli_malformed_reports_exit_2_json(self):
        p=self.root/'bad.drawio';p.write_text('bad')
        result=subprocess.run([sys.executable,str(SCRIPTS/'verify.py'),str(p),str(self.svg('')),'--json'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn('INCOMPLETE',result.stdout)

    def test_export_does_not_overwrite_by_default(self):
        source=self.source();(self.root/'source.svg').write_text('original')
        with self.assertRaises(FileExistsError): export(source,formats=['svg'],binary='unused')
        self.assertEqual((self.root/'source.svg').read_text(),'original')

    def test_builder_escapes_and_preserves_end_symbols(self):
        d=Diagram();d.class_box('a','A<T>',['+ x: A & B'],[],0,0);d.node('b','B',400,0)
        d.edge('e','a','b','composition');p=self.root/'builder.drawio';d.write(p)
        root=ET.parse(p)
        self.assertIn('startArrow=diamond;startFill=1;',root.find('.//mxCell[@id="e"]').get('style'))
        self.assertIn('A&lt;T&gt;',root.find('.//mxCell[@id="a"]').get('value'))


if __name__=='__main__': unittest.main()
