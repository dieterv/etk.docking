
import pygtk
pygtk.require('2.0')

from freshen import Before, After, AfterStep, Given, When, Then, scc as world
import gtk
from etk.docking import DockPaned, DockGroup, DockLayout, DockFrame, DockItem
from etk.docking.dnd import DRAG_TARGET_ITEM_LIST, DockDragContext
from etk.docking.docklayout import drag_motion, drag_end, drag_failed


class StubContext(object):
    def __init__(self, source_widget, items):
        self.targets = [ DRAG_TARGET_ITEM_LIST[0] ]
        self.source_widget = source_widget
        # Set up dragcontext (nornally done in motion_notify event)

        if items:
            self.source_widget.dragcontext = dragcontext = DockDragContext()
            dragcontext.dragged_object = items

    def get_source_widget(self):
        return self.source_widget

    def finish(self, success, delete, timestamp):
        self.finished = (success, delete)
    
    docklayout = property(lambda s: world.layout)


@After
def tear_down(_):
    world.window.destroy()
 

@Given('a window with (\d+) dockgroups?')
def default_window(n_groups):
    world.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    world.window.set_default_size(800, 150)
    world.frame = DockFrame()
    world.window.add(world.frame)
    world.layout = DockLayout()
    world.layout.add(world.frame)
    paned = DockPaned()
    world.frame.add(paned)
    world.window.show()
    world.frame.show()
    paned.show()
    world.groups = []
    for i in range(int(n_groups)):
        group = DockGroup()
        paned.add(group)
        group.show()
        world.groups.append(group)


@Given('(one|another) containing (\d+) items')
def setup_items(one_other, n_items):
    if one_other == 'one':
        index = 0
    else:
        index = world.item_index + 1
    for n in range(int(n_items)):
        button = gtk.Button()
        item = DockItem(icon_name='file', title='Item %s' % n, title_tooltip_text='')
        item.add(button)
        item.show()
        world.groups[index].add(item)
    world.item_index = index


@Given('start a main loop')
def start_a_main_loop():
    world.window.show_all()
    # simulate gtk.main()
    while gtk.events_pending():
       gtk.main_iteration()


@Given('define dockgroup (\d+) as "([^"]+)"')
def define_group_by_name(nth_group, name):
    group = world.groups[int(nth_group) - 1]
    #print 'Define group', group, 'as', name
    setattr(world, name, group)


@Given('define item (\d+) from dockgroup (\d+) as "([^"]+)"')
def define_item_by_name(nth_item, nth_group, name):
    group = world.groups[int(nth_group) - 1]
    item = group.get_children()[int(nth_item) - 1]
    #print 'Define item', item, 'as', name
    setattr(world, name, (group, item))


@When('I drag item "([^"]+)"')
def drag_item(name):
    group, item = getattr(world, name)
    assert item in group.items
    group.dragcontext.source_x = 1
    group.dragcontext.source_y = 1
    group.dragcontext.source_button = 1
    group.dragcontext.dragged_object = [ item ]
    world.dragged_items = group, [ item ]
    group.do_drag_begin(context=None)
    assert item.get_parent() is None
    #import time
    #time.sleep(1000)


@When('I drag all items in group "([^"]+)"')
def drag_all_items_in_group(name):
    group = getattr(world, name)
    group.dragcontext.source_x = 1
    group.dragcontext.source_y = 1
    group.dragcontext.source_button = 1
    group.dragcontext.dragged_object = [ item for item in group.items ]
    world.dragged_items = group, group.dragcontext.dragged_object
    group.do_drag_begin(context=None)


def drop_item(dest, x, y):
    source_group, items = world.dragged_items

    world.drop_pos = x, y

    context = StubContext(source_group, items)
    drag_data = drag_motion(dest, context, x, y, 0)

    assert drag_data, "No data from motion over %s at (%d, %d)" % (dest, x, y)

    drag_data.received(selection_data=None, info=None)

    del world.dragged_items
    world.dropped_items = items
    world.dropped_on_dest = dest

    drag_end(source_group, StubContext(source_group, items))

    groups = world.layout.get_widgets('EtkDockGroup')
    world.new_groups = list(set(groups).difference(world.groups))
    world.groups = groups


@When('I drop it on the content section in group "([^"]+)"')
def drop_item_on_content(name):
    dest_group = getattr(world, name)

    a  = dest_group.allocation
    
    x, y = a.x + a.width / 2, a.y + a.height / 2
    drop_item(dest_group, x, y)


@When('I drop it on tab "([^"]+)" in group "([^"]+)"')
def drop_item_on_tab(tabname, groupname):
    dest_group = getattr(world, groupname)
    dg2, item = getattr(world, tabname) 

    assert dg2 is dest_group

    assert item in dest_group.items
    tab = [tab for tab in dest_group._tabs if tab.item is item][0]
    a = tab.area
    x, y = a.x + a.width - 2, a.y + a.height - 2
    drop_item(dest_group, x, y)


@When('I drop it between groups "([^"]+)" and "([^"]+)"')
def drop_between_groups(group1name, group2name):
    group1 = getattr(world, group1name)
    group2 = getattr(world, group2name)
    paned = group1.get_parent()

    # Test is restricted to two groups having the same DockPaned as parent
    assert paned is group2.get_parent()

    index = [i.child for i in paned._items].index(group1)
    assert index == [i.child for i in paned._items].index(group2) - 1
    handle = paned._handles[index]

    x, y = handle.area.x + handle.area.width / 2, handle.area.y + handle.area.height / 2
    drop_item(paned, x, y)


@When('I drop it before the first group')
def drop_before_first_group():
    first_group = world.groups[0]
    a = first_group.allocation
    x, y = a.x, a.y + a.height / 2
    drop_item(first_group, x, y)


@When('I drop it outside of the frame')
def drop_it_outside_of_the_frame():
    source_widget, items = world.dragged_items
    drag_failed(source_widget, StubContext(source_widget, items), 1)
    world.new_frame = world.layout.get_floating_frames().next()


@Then('item "([^"]+)" is part of "([^"]+)"')
#@Then('item "(drag-me)" is part of "(to-group)"')
def then_tab_on_group(item_name, group_name):
    _, item = getattr(world, item_name)
    group = getattr(world, group_name)
    assert item in group.items


@Then('item "([^"]+)" is not part of "([^"]+)"')
def then_tab_not_on_group(item_name, group_name):
    _, item = getattr(world, item_name)
    group = getattr(world, group_name)
    assert item not in group.items


@Then('it has the focus')
def then_it_has_the_focus():
    assert len(world.dropped_items) == 1
    assert world.dropped_on_dest._current_tab.item is world.dropped_items[0]


@Then('it has been placed in just before "([^"]+)"')
def placed_before_tab(name):
    newgroup, item = getattr(world, name)
    start_a_main_loop()
    assert len(world.dropped_items) == 1
    items = newgroup.visible_items
    print 'it has been placed in just before', items.index(world.dropped_items[0]),
    print items.index(item) 
    assert items
    assert items.index(world.dropped_items[0]) == items.index(item) - 1
    

@Then('a new group should have been created')
def then_new_group():
    assert len(world.new_groups) == 1


@Then('it should contain the item')
def then_contains_item():
    items = world.new_groups[0].items
    assert set(world.dropped_items).issubset(items), (world.dropped_items, items)


@Then('the group "([^"]+)" has been removed')
def the_group_has_been_removed(group):
    group = getattr(world, group)
    assert group.get_parent() is None, group.get_parent()


@Then('a floating window is created')
def new_window_is_created():
    assert len(list(world.layout.get_floating_frames())) == 1


@Then('it contains a new group with the item')
def contains_a_new_group_with_the_item():
    group, items = world.dragged_items
    assert len(items) == 1

    assert items[0].get_parent() is not group
    assert items[0].get_ancestor(DockFrame) is world.new_frame

# vim:sw=4:et:ai
