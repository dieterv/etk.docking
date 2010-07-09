from freshen import Before, After, AfterStep, Given, When, Then, scc
import gtk
from etk.docking import DockPaned, DockGroup, DockLayout, DockFrame, DockItem
from etk.docking.dockgroup import DRAG_TARGET_ITEM_LIST


def event(widget, event_type, **kwargs):
    e = gtk.gdk.Event(event_type)
    for k, v in kwargs.items():
        print e, k, v
        setattr(e, k, v)
    e.window = widget.window
    #widget.event(e)
    #_gtk.main_do_event(e)
    return e

def do_event(widget, event_type, **kwargs):
    e = event(widget, event_type, **kwargs)
    gtk.main_do_event(e)


@AfterStep
def with_iteration(scc=None):
    """
    Make sure the gtk+ main loop runs after the step.
    """
    while gtk.events_pending():
        gtk.main_iteration()


@Before
def set_up(_):
    pass
    # DockGroup.drag_dest_find_target
    # DockGroup.drag_get_data

@After
def tear_down(_):
    scc.window.destroy()
 

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
    print 'Define tab', item, 'as', name
    setattr(scc, name, (group, item))


@Given('I drag item "([^"]+)"')
def drag_item(name):
    group, item = getattr(scc, name)
    for tab in group.visible_tabs:
        if tab.item is item:
            #do_event(group, gtk.gdk.BUTTON_RELEASE, x=tab.area.x + 1.,
            #         y=tab.area.y + 1., button=1)
            group.dragcontext.source_x = 1
            group.dragcontext.source_y = 1
            group.dragcontext.source_button = 1
            e = event(group, gtk.gdk.MOTION_NOTIFY, x=tab.area.x + 15.,
                     y=tab.area.y + 15., state=gtk.gdk.BUTTON1_MASK)
            scc.drag_context = group._start_dragging(e)
            break
    else:
        assert 0, 'item not found'
    print 'start drag for item'
    assert group.dragcontext.dragging
    assert group.dragcontext.source_button == 1, group.dragcontext.source_button 

@When('I drop it on the content section in group "([^"]+)"')
def drop_item(name):
    group = getattr(scc, name)
    a  = group.allocation
    
    # gdk.drag_find_window
    # gdk.drag_motion
    # gdk.drag_
    rox, roy = group.window.get_root_origin()
    rx, ry = rox + 40., roy + 100.
    #drag_window = gtk.Window()
    #drag_window.show()
    #dest_win, prot = scc.drag_context.drag_find_window(drag_window.window, rx, ry)
    #print 'Drop', dest_win, prot
    #scc.drag_context.drag_motion(dest_win, prot, rx, ry, gtk.gdk.ACTION_MOVE, gtk.gdk.ACTION_MOVE, 0)
    #do_event(group, gtk.gdk.DRAG_MOTION, x_root=rx,
    #         y_root=ry, send_event=False, time=0)
    #do_event(group, gtk.gdk.DROP_START, x_root=rx,
    #         y_root=ry, send_event=False, time=0)
    #do_event(group, gtk.gdk.MOTION_NOTIFY, x=a.x + 10.,
    #         y=a.y + a.height - 15., state=gtk.gdk.BUTTON1_MASK)
    #do_event(group, gtk.gdk.BUTTON_RELEASE, x=a.x + 10.,
    #         y=a.y + a.height - 15., state=gtk.gdk.BUTTON1_MASK)

    target = group.drag_dest_find_target(scc.drag_context, [DRAG_TARGET_ITEM_LIST])
    scc.drag_context.is_source = True
    group.drag_get_data(scc.drag_context, target, 0)

    print 'dropping item'

@Then('item "([^"]+)" is part of "([^"]+)"')
def then_tab_on_group(item_name, group_name):
    print 'tab is on group'
    assert 0
    _, item = getattr(scc, item_name)
    group = getattr(scc, group_name)
    for tab in group.visible_tabs:
        if tab.item is item:
            return
    else:
        assert 0, 'item not in group'

@Then('it has the focus')
def then_it_has_the_focus():
    print 'it has the focus'

# vim:sw=4:et:ai
