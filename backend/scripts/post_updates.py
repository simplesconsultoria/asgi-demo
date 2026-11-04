# /// script
# requires-python = ">=3.12"
# dependencies = ["plone-client>=1.0.0a4"]
# ///
"""Post updates to a Breaking News story at a steady pace, for live demos.

Every update goes through plone.restapi, with plone-client, as an editor's
would, so readers with the story open see each one arrive::

    uv run --script scripts/post_updates.py
    uv run --script scripts/post_updates.py --interval 10 --count 5

It posts the updates below in order, one every ``--interval`` seconds, and
stops after the last one (or after ``--count``). Updates whose title the
story already has are skipped, so a second run picks up where the first
stopped. Ctrl-C stops it at once.

The credentials come from ``PLONE_CLIENT_USERNAME`` and
``PLONE_CLIENT_PASSWORD`` (default ``admin``/``admin``). The events and
figures are fictional, like the rest of the example story.
"""

from plone_client import PloneClient
from plone_client.exceptions import PloneClientError

import argparse
import os
import sys
import time


UPDATES: list[dict[str, str]] = [
    {
        "title": "Good evening, we are back",
        "body": "Our live coverage continues tonight with reactions to the "
        "first-round result and the start of the second-round campaign.",
        "image": "newsroom",
    },
    {
        "title": "Electoral court publishes final turnout",
        "body": "Turnout closed at 79.4%, slightly above the last general "
        "election. Abstention was highest in the North region.",
        "image": "turnout-chart",
    },
    {
        "title": "Second-round campaigns relaunch",
        "body": "Both campaigns held their first strategy meetings of the "
        "runoff this afternoon. Free airtime on radio and TV starts on Friday.",
    },
    {
        "title": "Third-placed candidate stays neutral",
        "body": "The candidate who finished third said the party will not "
        "endorse anyone in the runoff and will let its voters decide.",
    },
    {
        "title": "Markets react to the result",
        "body": "The currency strengthened 1.2% against the dollar in "
        "after-hours trading, and the main index futures point higher.",
    },
    {
        "title": "First runoff poll out tomorrow",
        "body": "Pollsters confirmed the first survey of the second round "
        "will be released at 18:00 tomorrow.",
    },
    {
        "title": "Congress gets a new shape",
        "body": "With every seat counted, no party holds more than 15% of "
        "the Chamber of Deputies. Coalition talks are already under way.",
        "image": "national-congress",
    },
    {
        "title": "Fifteen states head to a runoff",
        "body": "Twelve states chose their governor today. The other fifteen "
        "go to a runoff on the same day as the presidential vote.",
        "image": "results-map",
    },
    {
        "title": "Debate dates proposed",
        "body": "Broadcasters proposed three runoff debates. Both campaigns "
        "accepted two of them; the third is still being negotiated.",
        "image": "debate-stage",
    },
    {
        "title": "Voting machine audit completed",
        "body": "Independent auditors found every sampled machine matched "
        "its printed tally. The full report is due next week.",
        "image": "voting-machine",
    },
    {
        "title": "Supporters gather in the capitals",
        "body": "Crowds are still celebrating in several state capitals. "
        "Police report no incidents so far.",
        "image": "celebration",
    },
    {
        "title": "Ballots stored for the runoff",
        "body": "Election officials began sealing and storing materials for "
        "the second round, in four weeks' time.",
        "image": "ballot-box",
    },
    {
        "title": "Turnout campaign announced",
        "body": "The electoral court will run a national campaign to bring "
        "abstainers back to the polls for the runoff.",
        "image": "polling-station",
    },
    {
        "title": "Good night from Brasília",
        "body": "That is all from us tonight. Coverage of the second round "
        "starts tomorrow morning. Thank you for reading.",
        "image": "sunset-over-brasilia",
    },
]


def image_uids(client: PloneClient, folder: str) -> dict[str, str]:
    """Map image ids to UIDs, to link them from an update's body.

    :param client: The plone-client client.
    :param folder: The path of the folder holding the images.
    :returns: Image id to UID; empty when the folder does not exist.
    """
    if not client.content.exists(folder):
        return {}
    return {
        item["@id"].rsplit("/", 1)[-1]: item["UID"]
        for item in client.content.children(
            folder, portal_type="Image", metadata_fields="UID"
        )
    }


def body_html(entry: dict[str, str], uids: dict[str, str]) -> str:
    """The update's body, with its image first when the site has it.

    :param entry: An entry from :data:`UPDATES`.
    :param uids: Image id to UID, from :func:`image_uids`.
    :returns: The body as HTML.
    """
    html = f"<p>{entry['body']}</p>"
    uid = uids.get(entry.get("image", ""))
    if uid:
        html = (
            f'<p><img class="image-richtext" alt="" '
            f'src="resolveuid/{uid}/@@images/image/large" /></p>{html}'
        )
    return html


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    :param argv: The command-line arguments.
    :returns: The parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Post updates to a Breaking News story at a steady pace."
    )
    parser.add_argument(
        "--url",
        default="http://asgi-demo.localhost",
        help="the site's URL (default: %(default)s)",
    )
    parser.add_argument(
        "--story", default="brazil-2026", help="the story's path (default: %(default)s)"
    )
    parser.add_argument(
        "--images", default="images", help="the images folder (default: %(default)s)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=20,
        help="seconds between updates (default: %(default)s)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=len(UPDATES),
        help="how many updates to post (default: all %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Post the updates the story does not have yet, one per interval.

    :param argv: The command-line arguments.
    :returns: The exit status.
    """
    args = parse_args(argv)
    with PloneClient(
        args.url,
        username=os.environ.get("PLONE_CLIENT_USERNAME", "admin"),
        password=os.environ.get("PLONE_CLIENT_PASSWORD", "admin"),
    ) as client:
        uids = image_uids(client, args.images)
        posted = {
            item["title"]
            for item in client.content.children(
                args.story, portal_type="BreakingNewsUpdate"
            )
        }
        entries = [entry for entry in UPDATES if entry["title"] not in posted]
        entries = entries[: max(args.count, 0)]
        if not entries:
            print(f"{args.story} already has every update.")
        for position, entry in enumerate(entries, start=1):
            if position > 1:
                time.sleep(args.interval)
            update = client.content.create(
                args.story,
                "BreakingNewsUpdate",
                title=entry["title"],
                body={
                    "data": body_html(entry, uids),
                    "content-type": "text/html",
                    "encoding": "utf-8",
                },
            )
            print(
                f"[{position}/{len(entries)}] {entry['title']}: {update['@id']}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
    except PloneClientError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
