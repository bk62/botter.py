# botter.py

A more ambitious discord bot starting from basic-discord-bot ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1))


Includes `sqlalchemy` ORM with Sqlite and jinja2 for templating.

WIP


## Quickstart

1. Follow the instructions [here](https://discordpy.readthedocs.io/en/stable/discord.html) to get your token and bot owner id and store these in an env file or replit secrets
2. Review `settings.py`
3. Run `python run.py initdb`
4. Run `python run.py run`
5. Run `bp*help` in your guild to view commands

### Economy

6. Add one or more virtual currencies
7. Set default currencies

## Key Ideas


### Parsing

I think one of the more interesting things I could try to do when developing a discord bot is try figure out ways to use custom syntaxes and parsers to help make these bot more useful without making it too complicated.

`discord.py` provides convenient command argument parsing but lots of nesting can become convoluted and perplexing.

For example, I wanted to add the ability to create, update and delete virtual currencies. A simple model for a virtual currency is,

```
currency: {
    name:, code:, symbol:, description
}
```

Using bot commands, I needed a way to get structured user input comparable to using web forms. Using command arguments a solution could be:

`bp*currency add <name> <code> <symbol> <description>`

Which is fine but what if I wanted to add more fields and/or related models (corresponding to embedded formsets in django for example). Specifically, for this project, I also wanted to add the ability to parse strings containing currency denominations (e.g. "1 buck, 2 quarters, 3 cents") which meant that I had to add denominations data to the database. Which would mean I had to implement complicated nesting or the user had to run multiple commands to add a single virtual currency.

Adding a simple parsing grammar was, arguably, therefore the simpler more extendible solution. Take for example the following currency specification:

```
currency UsDollar USD
description "National Currency of the US"
denominations buck 1, penny 0.01, grand 1000
```

The economy extension, (using the `CurrencySpec` grammar and parser) is able to parse it and creates the corresponding ORM models for currencies and denominations allowing commands like,


`bp*gamble 1 grand`



### NLP

WIP
Simple analysis of text channel history.
 
## Setup

Store bot secret token and owner id in env vars called `TOKEN` and `BOT_OWNER_ID` respectively as in `.env.example` file.

Command prefix and enabled extensions can be configured in settings.py


## Usage

### Run

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



## Development

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

### TODO




## References

+ `basic-discord-bot` ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1)) 
+ https://discordpy.readthedocs.io/en/latest
+ https://docs.sqlalchemy.org/


## License
[MIT](https://choosealicense.com/licenses/mit/)