from keep_alive import keep_alive as flask_keep_alive
import main
import click


@click.command()
@click.option('--keep-alive', default=False, help='Run flask thread to keep Repl alive.')
def run(keep_alive):
    """Run the Discord bot."""
    if keep_alive:
        flask_keep_alive()

    main.main()


if __name__ == '__main__':
    run()