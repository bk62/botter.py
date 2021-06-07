#!/usr/bin/env python3
import asyncio
import os
import logging

from keep_alive import keep_alive as flask_keep_alive
import main, db, economy
import settings
import click


logger = logging.getLogger('run')

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
            click.echo('[*] Dropping db...')
            logger.info('Dropping db')
            await conn.run_sync(db.Base.metadata.drop_all)
        if init:
            click.echo('[*] Creating db...')
            logger.info('Creating db')
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
    logger.info('Clearing replit-db')
    for k in db.replit_db.keys():
        del db.replit_db[k]

@cli.command('init')
@click.option('--force', is_flag=True, help='Force adding defaut currency if db already exists.')
def init(force):
    """
    Initialize a new project.
    
    Creates a database and creates a default currency.
    """
    no_db = not os.path.exists(settings.DB_PATH)
    if (no_db):
        click.echo('[+] No DB. Creating...')
        initdb()
        click.echo('[+] Done.')
    if (no_db or force):
        logger.info('Adding intial currency')
        click.echo('[+] Adding a currency...')
        economy.create_default_currency()
    else:
        click.echo('[-] DB exists. Not creating currency. Add "--force" to force.')


if __name__ == '__main__':
    cli()
