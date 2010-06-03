:class:`DockLayout`
===================

The DockLayout class is responsible for maintaining the layout of `DockPaned`
and `DockGroup` elements. This is done by applying a role `PartOfLayout` to
the element. this role implies that important calls (mainly DnD) are intercepted
and allow the container to draw indicators where containers will be placed.

This `PartOfLayout` role will intercept all calls for adding and removing and
makes sure all child items will also be `PartOfLayout`. This is done by signal callbacks.



.. autoclass:: etk.docking.DockLayout
    :show-inheritance:
    :members:
