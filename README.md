# botter.py

A more ambitious discord bot starting from basic-discord-bot ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1))


Includes `sqlalchemy` ORM with Sqlite and jinja2 for templating.

WIP


## Quickstart

1. Follow the instructions [here](https://discordpy.readthedocs.io/en/stable/discord.html) to get your token and bot owner id and store these in an env file or replit secrets
2. Review `settings.py`
3. Run `python run.py init`
4. Run `python run.py run`
5. Run `bp*help` in your guild to view commands

### Economy

6. Run `bp*currency list` to view auto-added currency.
7. Add one or more virtual currencies
7. Set default currencies

## Key Ideas


### Parsing
I think one of the more interesting things I could try to do with a discord bot is try figure out ways to use custom syntaxes and parsers to help make these bot more useful without making it too complicated.

#### Currency 


`discord.py` provides convenient and expressive command argument parsing but lots of nesting can become convoluted and perplexing. Especially since I planned to add CRUD functionality, I needed ways to get structured user input comparable to using web forms or AJAX POSTS with JSON.

For example, I wanted to add the ability to create, update and delete virtual currencies. A simple model for a virtual currency is;

```
currency: {
    name:, code:, symbol:, description
}
```

Using command arguments a solution could be:

`bp*currency add <name> <code> <symbol> <description>`

Which is fine but what if I wanted to add more fields and/or related models (corresponding to nesting arrays in JSON or embedded formsets in django). Specifically, for this project, I also wanted to add the ability to parse strings containing currency denominations (e.g. "1 buck, 2 quarters, 3 cents") which meant that I had to add denominations data to the database. Which would mean I had to implement complicated nesting or the user had to run multiple commands to add a single virtual currency.

Adding a simple parsing grammar was, arguably, therefore the simpler more extendible solution. Take for example the following currency specification:

```
currency UsDollar USD
description "National Currency of the US"
denominations buck 1, penny 0.01, grand 1000
```

The economy extension, (using the `CurrencySpec` grammar and parser) is able to parse it and creates the corresponding ORM models for currencies and denominations allowing commands to take simple currency amount strings (like `2 grand, 40 bucks, 5 penny`) as input e.g.,


`bp*gamble 1 grand`

(`economy.parsers` contains the `pyleri` grammar definitions and parsers for parsing currency definition specs and currency amount strings.)

#### Reward Policies


WIP - Doesn't work yet.

The idea here was to let guild admins define reward policies with a simple DSL -- intended to be more of a proof of concept than an efficient execution.

For example, the following rule would reward new members (assuming a currency with symbol BTC was previously added)
```
rule join_bonus
    event member join
    reward 1 BTC to member
end
```

You can add conditions too (and comments):
```
// Similar to encouragements bot in freecodecamp tutorial
rule cheer_up
    event message send
    conditions [
        content *= 'sad' and not content *= 'happy'
    ]
    reward 1 BTC to author
end
```

The `*=` operator is similar to CSS attribute selector. (`^=`, `$=` etc also work similarly.)


The following rule is a bit more complicated with multiple conditions and nested attribute access.
```
// Say hi in general channel
// or thank people in help channel
// Note: you can condition on nested attributes using '__'
// Note: multiple conditions are separated by commas
// and are combined with an 'OR'
rule polite_bonus
    event message send
    conditions [
        content ~= 'hi' and channel__name == 'general',
        content ~= 'thank' and channel__name == 'help'
    ]
    reward 1 BTC to author
end
```
Similarly to Django ORM queries, you can add `__` to access nested attributes. Multiple conditions can being added and are combined with an 'OR' operator.


Attributes like 'channel' and 'content' are added depending on the event and the context. Since this is a work in progress, the errors are opaque and there is no documentation.

Here are a few more examples:

```
// Reply in the help channel *or* reply with welcome anywhere
// Note: No parenthesis so left to right precedence
// multiple rewards
rule help_bonus
    event message send
    conditions [
        reply == true and channel__name == 'help' or content *= 'welcome'
    ]
    reward 1 BTC to original_author
    reward 1 BTC to author
end



// Both message author and reactor get bonuses in general channel
// reactions
rule reactions_in_general
    event reaction add
    conditions [
        channel__name == 'general'
    ]
    // original_author = message author
    reward 2 BTC to original_author
    // author = reactor
    reward 1 BTC to author
end


// First to react with new reaction in announcements gets a bonus
// TODO lt, gt etc
rule first_to_react_announcements
    event reaction add
    conditions [
        channel__name == 'announcements' and reaction__count == 1
    ]
    reward 3 btc to author
end

```
A policy document contains multiple rules. The `economy.cogs.rewards.Rewards` cog handles adding event listeners to enforce each rule.

(The implementation of the DSL (using textx) is in `economy/rewards_dsl`.)


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
In addition to the simple extensions from `basic-discord-bot`,

#### Economy
- Currencies - create and update multiple virtual currrencies using custom grammar
- Wallet - deposits, withdrwals and payments in all the virtual currencies defined in the project
- Rewards - define reward policies using a custom DSL
- Gambling - gamble with virtual currencies


### WIP

 - economy
 - nlp

### TODO

Also see the commented TODO notes throughout the project.

### Known issues

Lots of bug fixing, refactoring and rewriting needed as its being written by one person over a few days. 

But, the following will probably be on the backburner for a while:
- `bp*admin` extension reloading doesn't seem play well with econ ext. 
- Currency code and symbol attribute used inconsistently.
- Error handling is non-existent.
- I have created ORM models for guilds and channels but am not using them. And, since I'm using replitdb in a simplistic way to store defaults, needs work before using in multiple servers.

## References

+ `basic-discord-bot` ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1)) 
+ https://discordpy.readthedocs.io/en/latest
+ https://docs.sqlalchemy.org/


## License
[MIT](https://choosealicense.com/licenses/mit/)