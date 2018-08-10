Serialization
=============

One of the required features is to be able to persist and load a layout.
This can be done by means of the DockStore. A DockStore is able to load and save layouts.
For loading and saving, the most simple xml serializer is used: xml.parser or etree::

    <?xml version="1.0" encoding="utf-8">
    <layout>
      <frame x="0" y="0" width="0" height="0">
    <paned orientation="horizontal">
      <group size="23%">
        <item id="identifier" title="" icon="" tooltip="" pos="1" vispos="2" />
      </group>
      <paned size="67%" orientation="vertical">
        <group size="100%">
          <item id="identifier2" title="" icon="" tooltip="" pos="1" vispos="2" />
        </group>
    </paned>
      </frame>
      <frame floating="true" x="0" y="0" width="0" height="0">
    ...
      </frame>
    </layout>

The layout can be set up automatically as far as DockFrame, DockPaned, DockGroup and DockItem is concerned. The contents of a single DockItem is harder to construct. For this the DockStore needs to consult a delegate object that implements the DockStore protocol::

   class DockStoreDelegate(object):
      def load(self, id): pass


Open items:

* It's interesting to see to what extend the current GUI builder code can suite us.

