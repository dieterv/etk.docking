from freshen import Before, After, AfterStep, Given, When, Then, scc
import gtk
from etk.docking import DockPaned, DockGroup, DockLayout, DockFrame, DockItem
from etk.docking.dockgroup import DRAG_TARGET_ITEM_LIST
from etk.docking.dnd import DockDragContext


#def event(widget, event_type, **kwargs):
#    e = gtk.gdk.Event(event_type)
#    for k, v in kwargs.items():
#        print e, k, v
#        setattr(e, k, v)
#    e.window = widget.window
#    #widget.event(e)
#    #_gtk.main_do_event(e)
#    return e

#def do_event(widget, event_type, **kwargs):
#    e = event(widget, event_type, **kwargs)
#    gtk.main_do_event(e)


class StubContext(object):
    def __init__(self, source_widget, tabs):
        self.targets = [ DRAG_TARGET_ITEM_LIST[0] ]
        self.source_widget = source_widget
        # Set up dragcontext (nornally done in motion_notify event)
        if tabs:
            self.source_widget.dragcontext = dragcontext = DockDragContext()
            dragcontext.dragged_object = tabs

    def get_source_widget(self):
        return self.source_widget

    def finish(self, success, delete, timestamp):
        self.finished = (success, delete)

class StubSelectionData(object):
    def set(self, atom, bytes, data):
        print 'StubSelectionData.set(%s, %s, %s)' % (atom, bytes, data)

@AfterStep
def with_iteration(scc=None):
    """
    Make sure the gtk+ main loop runs after the step.
    """
    while gtk.events_pending():
        gtk.main_iteration()


@Before
def set_up(_):
    def drag_get_data(widget, context, target, timestamp):
        with_iteration()
        selection_data = StubSelectionData()
        context.source_widget.do_drag_data_get(context, selection_data, None, timestamp)
        x, y = scc.drop_pos
        scc.layout.on_widget_drag_data_received(widget, context, x, y, selection_data, None, timestamp)

    DockGroup.drag_get_data = drag_get_data
    DockPaned.drag_get_data = drag_get_data
    DockFrame.drag_get_data = drag_get_data

@After
def tear_down(_):
    scc.window.destroy()
    del DockGroup.drag_get_data
    del DockPaned.drag_get_data
    del DockFrame.drag_get_data
 

@Given('a window with (\d+) dockgroups?')
def default_window(n_groups):
    scc.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    scc.window.set_default_size(800, 150)
    scc.frame = DockFrame()
    scc.window.add(scc.frame)
    scc.layout = DockLayout()
    scc.layout.add(scc.frame)
    paned = DockPaned()
    scc.frame.add(paned)
    scc.groups = []
    for i in range(int(n_groups)):
        group = DockGroup()
        paned.add(group)
        scc.groups.append(group)
    scc.window.show_all()

@Given('(one|another) containing (\d+) items')
def setup_items(one_other, n_items):
    if one_other == 'one':
        index = 0
    else:
        index = scc.item_index + 1
    for n in range(int(n_items)):
        button = gtk.Button()
        item = DockItem(icon_name='file', title='Item %s' % n, title_tooltip_text='')
        item.add(button)
        item.show_all()
        scc.groups[index].add(item)
    scc.item_index = index

@Given('define dockgroup (\d+) as "([^"]+)"')
def define_group_by_name(nth_group, name):
    group = scc.groups[int(nth_group) - 1]
    print 'Define group', group, 'as', name
    setattr(scc, name, group)

@Given('define item (\d+) from dockgroup (\d+) as "([^"]+)"')
def define_item_by_name(nth_item, nth_group, name):
    group = scc.groups[int(nth_group) - 1]
    item = group.get_children()[int(nth_item) - 1]
    print 'Define item', item, 'as', name
    setattr(scc, name, (group, item))


@Given('I drag item "([^"]+)"')
def drag_item(name):
    group, item = getattr(scc, name)
    for tab in group.visible_tabs:
        if tab.item is item:
            group.dragcontext.source_x = 1
            group.dragcontext.source_y = 1
            group.dragcontext.source_button = 1
            group.dragcontext.dragged_object = [ tab ]
            scc.dragged_tabs = group, [tab]
            break
    else:
        assert 0, 'item not found'
    print 'start drag for item'

def drop_item(dest, x, y):
    source_group, tabs = scc.dragged_tabs

    scc.drop_pos = x, y
    dropped_items = [tab.item for tab in tabs]

    context = StubContext(source_group, tabs)
    scc.layout.on_widget_drag_motion(dest, context, x, y, 0)

    scc.layout.on_widget_drag_drop(dest, context, x, y, 0)

    del scc.dragged_tabs
    scc.dropped_items = dropped_items
    scc.dropped_on_dest = dest
    print 'dropping item'

@When('I drop it on the content section in group "([^"]+)"')
def drop_item_on_content(name):
    dest_group = getattr(scc, name)

    a  = dest_group.allocation
    
    ox, oy = dest_group.window.get_root_origin()
    x, y = ox + a.width / 2, oy + a.height / 2
    drop_item(dest_group, x, y)

@When('I drop it on tab "([^"]+)" in group "([^"]+)"')
def drop_item_on_tab(tabname, groupname):
    dest_group = getattr(scc, groupname)
    dg2, item = getattr(scc, tabname) 

    assert dg2 is dest_group

    for tab in dest_group.tabs:
        if tab.item is item:
            break
    else:
        assert 0, 'item not found'

    ox, oy = dest_group.window.get_root_origin()
    x, y = tab.area.x + tab.area.width - 2, tab.area.y + tab.area.height - 2
    print 'Dropping on', tab.area, x, y
    drop_item(dest_group, x, y)

@When('I drop it between groups "([^"]+)" and "([^"]+)"')
def drop_between_groups(group1name, group2name):
    group1 = getattr(scc, group1name)
    group2 = getattr(scc, group2name)
    paned = group1.get_parent()

    # Test is restricted to two groups having the same DockPaned as parent
    assert paned is group2.get_parent()

    index = [i.child for i in paned.items].index(group1)
    assert index == [i.child for i in paned.items].index(group2) - 1
    handle = paned.handles[index]

    x, y = handle.area.x + handle.area.width / 2, handle.area.y + handle.area.height / 2
    drop_item(paned, x, y)

    groups = [i.child for i in scc.dropped_on_dest.items]
    scc.new_groups = list(set(groups).difference(scc.groups))
    scc.groups = groups

@When('I drop it before the first group')
def drop_before_first_group():
    raise NotImplemented, 'needs implementation'


@Then('item "([^"]+)" is part of "([^"]+)"')
def then_tab_on_group(item_name, group_name):
    _, item = getattr(scc, item_name)
    group = getattr(scc, group_name)
    print 'tab is on group', item
    for tab in group.tabs:
        print 'tab.item', tab.item
        if tab.item is item:
            print 'Have the item'
            return
    else:
        assert 0, 'item not in group'

@Then('it has the focus')
def then_it_has_the_focus():
    assert len(scc.dropped_items) == 1
    assert scc.dropped_on_dest._current_tab.item is scc.dropped_items[0]

@Then('it has been placed in just before "([^"]+)"')
def placed_before_tab(name):
    newgroup, item = getattr(scc, name)
    assert len(scc.dropped_items) == 1
    items = [tab.item for tab in newgroup.visible_tabs]
    print 'it has been placed in just before', items.index(scc.dropped_items[0]) , items.index(item) 
    assert items.index(scc.dropped_items[0]) == items.index(item) - 1
    
@Then('a new group should have been created')
def then_new_group():
    assert len(scc.new_groups) == 1

@Then('it should contain the item')
def then_contains_item():
    items = [t.item for t in scc.new_groups[0].tabs]
    assert set(scc.dropped_items).issubset(items), (scc.dropped_items, items)



# vim:sw=4:et:ai
