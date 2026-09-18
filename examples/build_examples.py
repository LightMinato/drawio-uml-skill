"""Build stable examples; before/after differ only in geometry."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'drawio-uml' / 'scripts'))
from uml_xml import Diagram

HERE = Path(__file__).resolve().parent


def classes(clean):
    d = Diagram('Order domain', 1100, 760)
    pos = {'customer': (60, 90), 'order': (420, 90), 'item': (780, 90), 'payment': (420, 420)} if clean else {
        'customer': (70, 170), 'order': (380, 350), 'item': (760, 80), 'payment': (340, 120)}
    data = [('customer','Customer',['+ id: UUID','+ name: String'],['+ placeOrder(): Order'],''),
            ('order','Order',['+ id: UUID','+ total: Money'],['+ submit()','+ cancel()'],''),
            ('item','OrderItem',['+ quantity: int','+ unitPrice: Money'],['+ subtotal(): Money'],''),
            ('payment','PaymentGateway',[],['+ charge(total: Money): Receipt'],'interface')]
    for cid,name,attrs,ops,st in data:
        d.class_box(cid,name,attrs,ops,*pos[cid],w=240,h=160,stereotype=st)
    d.edge('places','customer','order',label='places',style='exitX=1;exitY=0.5;entryX=0;entryY=0.5;',points=() if clean else [(650,250),(650,430)])
    d.endpoint_label('customer-one','places','1','source',(-10,-22))
    d.endpoint_label('orders-many','places','0..*','target',(10,-22))
    d.edge('contains','order','item','composition',style='exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
    d.endpoint_label('order-one','contains','1','source',(-10,-22))
    d.endpoint_label('items-many','contains','1..*','target',(10,-22))
    d.edge('uses','order','payment','dependency',label='«use»',style='exitX=0.5;exitY=1;entryX=0.5;entryY=0;')
    d.write(HERE / ('class-after.drawio' if clean else 'class-before.drawio'))


def sequence():
    d = Diagram('Checkout sequence', 1000, 650)
    for cid, name, x in [('ui','Checkout UI',80),('service','Order service',390),('gateway','Payment gateway',700)]:
        d.node(cid,name,x,60,200,55)
        d.edge(cid+'-life',None,None,style='edgeStyle=none;dashed=1;strokeColor=#94A3B8;',start=(x+100,115),end=(x+100,530))
    for cid,kind,label,start,end in [('submit','call','1: submit(order)',(180,190),(490,190)),('charge','call','2: charge(total)',(490,280),(800,280)),('receipt','reply','3: receipt',(800,370),(490,370)),('confirm','reply','4: confirmation',(490,460),(180,460))]:
        d.edge(cid,None,None,kind,label,style='edgeStyle=none;',start=start,end=end)
    d.write(HERE/'sequence.drawio')

if __name__ == '__main__':
    classes(False); classes(True); sequence()
