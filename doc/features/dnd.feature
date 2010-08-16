Feature: Drag and drop tabs

  Background:
    Given a window with 2 dockgroups
    And one containing 3 items
    And another containing 2 items
    And define dockgroup 1 as "some-group"
    And define dockgroup 2 as "to-group"
    And define item 1 from dockgroup 1 as "drag-me"
    And define item 1 from dockgroup 2 as "sometab"

  Scenario: Drag an item over a new group
    Given I drag item "drag-me"
    When I drop it on the content section in group "to-group"
    Then item "drag-me" is part of "to-group"
    And it has the focus

  Scenario: Drag an item over the tabs of a new group.
    Given I drag item "drag-me"
    When I drop it on tab "sometab" in group "to-group"
    Then item "drag-me" is part of "to-group"
    And it has the focus
    And it has been placed in just before "sometab"

  Scenario: Drag an item and drop it between two existing groups.
    Given I drag item "drag-me"
    When I drop it between groups "some-group" and "to-group"
    Then a new group should have been created
    And it should contain the item

  Scenario: Drag an item to the end of a group of DockGroups.
    Given I drag item "drag-me"
    When I drop it before the first group
    Then a new group should have been created
    And it should contain the item

  Scenario: Drag an item at the begin/end of the intersection between groups
    The paned widget should get a new parent with opposite orientation,
    containing the items in a new group.

  Scenario: If the last item from a group is moved to somewhere else,
    Given I drag all items in group 'somegroup'
    When I drop it on the content section in group "to-group"
    Then the group "somegroup" should have been removed

  Scenario: Remove last item from DockGroup and containing DockPaned is also empty
    If there is a parent paned that contains only one item after the removal,
    it should also be removed (recursively)

  Scenario: If an item is dragged ourside the scope of the dock frame.
    Given I drag item "drag-me"
    When I drop it outside of the frame
    Then a new window should be created
    And it should contain a new group with the item

