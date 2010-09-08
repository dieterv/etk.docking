
from xml.etree.ElementTree import Element, SubElement, tostring

tree = Element('toplevel')

root = SubElement(tree, 'root', {})
e1 = SubElement(root, 'sub1', {})
e2 = SubElement(root, 'sub2', {'a':"1"})

print tostring(tree)
