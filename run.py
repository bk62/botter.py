#!/usr/bin/env python3
import asyncio
from keep_alive import keep_alive as flask_keep_alive
import main
import db
import click



@click.group()
def cli():
    pass


@cli.command()
@click.option('--keep-alive', is_flag=True, help='Run flask thread to keep Repl alive.')
def run(keep_alive):
    """Run the Discord bot."""
    if keep_alive:
        flask_keep_alive()

    main.main()


async def _run_db(init=True, drop=False):
    main.init_extensions()
    async with db.engine.begin() as conn:
        if drop:
            click.echo('Dropping...')
            await conn.run_sync(db.Base.metadata.drop_all)
        if init:
            click.echo('Creating...')
            await conn.run_sync(db.Base.metadata.create_all)


@cli.command('initdb')
def initdb():
    """Create all tables."""
    asyncio.run(_run_db())


@cli.command('dropdb')
def dropdb():
    """Drop all tables."""
    asyncio.run(_run_db(init=False, drop=True))


@cli.command('resetdb')
def resetdb():
    """Reset all tables."""
    asyncio.run(_run_db(init=True, drop=True))

@cli.command('clearreplitdb')
def cleardb():
    """Empty replit-db."""
    for k in db.replit_db.keys():
        del db.replit_db[k]


if __name__ == '__main__':
    cli()
