:class:`etk.DockLayout`
=======================

.. autoclass:: etk.docking.DockLayout
    :show-inheritance:
    :members:

Signals
-------
item-closed ( group, item ): event forwarded from the DockGroup on which
the item was removed. This makes for easy central maintenance of how to deal
with closed items (e.g. if the items should be destroyed or not).
