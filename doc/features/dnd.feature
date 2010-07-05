Feature: Drag and drop tabs.

  Background:
    Given a window with 1 dockgroup each having 3 items
    And another dockgroup to the left containing 2 items

  Scenario: Drag an item over a new group
    Given I drag tab "somename"
    When I drop it on the content section in group "somegroup"
    Then tab "somename" is part of "somegroup"
    And it has the focus

  Scenario: Drag an item over the tabs of a new group.
    The items should be inserted at the position the items are dropped.
    Given I drag tab "somename"
    When I drop it on tab "sometab" in group "somegroup"
    Then tab "somename" is part of "somegroup"
    And it has the focus
    And it has been placed in just before "sometab"

  Scenario: Drag an item and drop it between two existing groups.
    Given I drag tab "somename"
    When I drop it between groups "somegroup" and "someothergroup"
    Then a new group should have been created
    And it should contain the tab

  Scenario: Drag an item to the end of a group of DockGroups.
    A new group should appear at that end containing the items
    Given I drag tab "somename"
    When I drop it before the first groups
    Then a new group should have been created
    And it should contain the tab

  Scenario: Drag an item at the begin/end of the intersection between groups
    The paned widget should get a new parent with opposite orientation,
    containing the items in a new group.

  Scenario: If the last item from a group is moved to somewhere else,
    the group should be removed.
    If there is a parent paned that contains only one item after the removal,
    it should also be removed (recursively)

  Scenario: If an item is dragged ourside the scope of the dock frame.
    Given I drag tab "sometab"
    When I drop it outside of the frame
    Then a new window should be created
    And it should contain a new group with the tab

