"""Tests for the live Breaking News machinery."""

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

IMAGE_FOLDER = {"type": "Document", "id": "images", "title": "Images"}

UPDATE = {
    "type": "BreakingNewsUpdate",
    "id": "polls-open",
    "title": "Polls open across the country",
}

# A 1x1 transparent PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d000000"
    "0049454e44ae426082"
)
