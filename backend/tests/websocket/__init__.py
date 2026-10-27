"""End-to-end tests of the reader's websocket, against a committed site."""

STORY = {
    "type": "BreakingNews",
    "id": "brazil-2026",
    "title": "Brazil Elections 2026",
}

PRIVATE_STORY = {
    "type": "BreakingNews",
    "id": "embargoed",
    "title": "Embargoed story",
}

#: A private section holding a published story: the catalog lets an anonymous
#: reader find the story, and only traversal stops them on the way to it.
PRIVATE_SECTION = {"type": "Document", "id": "newsroom", "title": "Newsroom"}

HIDDEN_STORY = {
    "type": "BreakingNews",
    "id": "draft-coverage",
    "title": "Draft coverage",
}

#: Updates added to the published story, oldest first.
UPDATES = (
    {"id": "polls-open", "title": "Polls open across the country"},
    {"id": "turnout", "title": "Turnout passes 50% by noon"},
)

POLICY_VIOLATION = 1008
