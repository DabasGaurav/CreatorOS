"""Manual niche-signal curation. No scraping, no automation — the founder enters
what's currently performing well among top accounts in a creator's niche."""

import click

from creatorsignal.db.base import get_session
from creatorsignal.niche.repository import add_niche_signal, list_niche_signal


@click.group()
def cli():
    pass


@cli.command("add")
@click.option("--niche", required=True, help="e.g. 'AI/startups'")
@click.option("--account", "account_handle", required=True, help="Instagram handle observed")
@click.option("--topic", "observed_topic", required=True, help="What's performing well")
@click.option("--added-by", required=True, help="Who entered this row")
@click.option("--note", default=None, help="Optional free-text note")
def add(niche: str, account_handle: str, observed_topic: str, added_by: str, note: str | None):
    session = get_session()
    row = add_niche_signal(
        session,
        niche=niche,
        account_handle=account_handle,
        observed_topic=observed_topic,
        added_by=added_by,
        note=note,
    )
    click.echo(f"Added niche_signal row {row.id} ({row.niche} / {row.account_handle})")


@cli.command("list")
@click.option("--niche", default=None, help="Filter to one niche")
def list_rows(niche: str | None):
    session = get_session()
    rows = list_niche_signal(session, niche=niche)
    if not rows:
        click.echo("No niche_signal rows found.")
        return
    for row in rows:
        click.echo(
            f"[{row.observed_at:%Y-%m-%d}] {row.niche} / {row.account_handle}: "
            f"{row.observed_topic} (by {row.added_by})"
        )


if __name__ == "__main__":
    cli()
