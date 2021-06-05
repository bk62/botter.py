# Basic Discord Bot


A more ambitious discord bot starting from basic-discord-bot ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1))

WIP


### Quickstart

1. Follow the instructions [here](https://discordpy.readthedocs.io/en/stable/discord.html) to get your token and bot owner id and store these in an env file or replit secrets
2. Review `settings.py`
3. Run `python run.py initdb`
4. Run `python run.py run`
5. Run `$help` in your guild to view commands

### Setup

Store bot secret token and owner id in env vars called `TOKEN` and `BOT_OWNER_ID` respectively as in `.env.example` file.

Command prefix and enabled extensions can be configured in settings.py


### Usage

#### Run

`python run.py run`

Also run flask web server to keep a Repl alive: 

`python run.py run --keepalive`

#### DB

Reset replit-db:

`python run.py clearreplitdb`

Init sqlite db:

`python run.py initdb`

Clear sqlitedb:

`python run.py cleardb`

Reset sqlitedb:

`python run.py resetdb`


### Project Structure

I tried to structure the project so that  extension packages are analogous to `Django` apps. Specifically, as loosely coupled with their own models, cogs and commands that *ideally* can be reused.


Settings are stored in a `settings.py` file.

Management commands can be added to `run.py` using [click](https://click.palletsprojects.com/).



### Extensions
- admin - manage `discord.py` extensions
- economy - extremely minimal virtual currency extension using replit-db
- encouragements - encouragements bot from freecodecamp tutorial (see below) put into a cog and extension
- greetings - minimal greetings bot verbatim from `discord.py` docs


### WIP

 - economy
 - nlp

### References

+ `basic-discord-bot` ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1)) 
+ https://discordpy.readthedocs.io/en/latest
+ https://docs.sqlalchemy.org/

### TODO



### License
[MIT](https://choosealicense.com/licenses/mit/)