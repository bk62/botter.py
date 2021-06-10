# botter.py

An experimental discord bot toolkit prototype that took a life of its own.

This project is more of an example to inspire ideas or to refer to when start your own bot projects than something ready to add to your server. I do intend to make this something ready to be added to a server. I'll have to revisit it when I can and rethink the aim, structure and whether to spin off some features/code to other repos.


I started writing this to participate in [https://1729.com/replit-discord](https://1729.com/replit-discord). 

This project is intended as an experiment and a learning experience and was built in about a week. So, there are lots of bugs, code repetition, not a single test written, and so on. 


## Quickstart

1. Follow the instructions [here](https://discordpy.readthedocs.io/en/stable/discord.html) to get your token and bot owner id and store these in an env file or replit secrets
2. Review `settings.py`
3. Run `python run.py init`
4. Run `python run.py run`
5. Run `bp*help` in your guild to view commands

### Economy

6. Run `bp*currency list` to view auto-added currency.
7. Add one or more virtual currencies



## Why

I just started looking into Discord bots. I started with the freecodecamp tutorial (referenced below), discord.py docs and replit templates. Getting simple examples to work was easy and I soon started seeing thinking of more ambitious bot projects to attempt. 

A problem I faced was structuring my bot projects so that it was relatively simple to build advanced functionalities. `discordpy.ext`'s commands, cogs and extensions were useful but since I was planning to integrate an ORM, I needed more structure. That's why I created a basic discord bot starter kit
([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1)) to get some experience with building more slightly less trivial bots.

Finally, I started this project to give life to some random ideas I had about what a discord bot could do while also gaining experience with `asyncio` in python, `SQLAlchemy` and discord bots -- all of which I'm inexperienced with.

First of all, anything more than trivial bots require data storage. Since I intended the bot would eventually store and query complex data and because it looked like a lot of fun, I decided to use `sqlalchemy`.

I also added `jinja2` for templating. Discord API embeds are really nifty but templating is very useful especially  to display text formatted to exploit the discord markdown code block coloring trick.

## Objectives and Principles

#### Modular and configurable
I have tried to use python best standards wherever possible.

I tried make 'extension' packages modular and only loosely coupled (similar to Django apps) so you could choose which ones to enable in each project. Eventually, the complications piled on so the code needs lots of cleanup. Also like Django, the `settings.py` file holds most of the project settings.

The `run.py` file holds all the commands for the project. Unfortunately, I haven't yet been able to reorganize it so all extension CLI commands are configured within itself.

I planned to add a couple extensions but the `economy` extension got out of hand and I only have the single example of the structure I planned.

#### Database integration with (some) separation of concerns

ideally, I didn't want the 'cogs' to be too concerned with database querying and session/transaction management.
Through lots of trial and error, I have stumbled on a structure that (almost) works for me:  
- `db.py` holds the project level initialization and models (user, guild and channel)
- Each extension has its own `models` package which is imported by `main`
- All query builders and async query methods stay in 'repositories' (see `economy.repositories`) 
- 'Services' are *supposed* to interface between repositories and cogs. (see `economy.services`) It's a bit of a mess right now, but I am quite pleased that the following APIs are possible:

```python
# ways to modify two models in the same DB transaction
# from a cog method -- so that both fail or succeed together

# 1.
async def change_names():
    async with self.service, self.service.session.begin:
        c1 = self.service.currency_repo.get(symbol='BPY')
        c2 = self.service.currency_repo.get(symbol='RC')
        c1.name = 'BotterPy'
        c2.name = 'RewardCoin'


# 2.a and 2.b
async def change_names2():
    async def change_names_inner():
        c1 = self.service.currency_repo.get(symbol='BPY')
        c2 = self.service.currency_repo.get(symbol='RC')
        c1.name = 'BotterPy'
        c2.name = 'RewardCoin'
    coro = change_names_inner()
    self.service(coro)
    # OR
    self.service.await_with(coro)

# ETC
```


I have almost exclusively used `sqlalchemy`'s new `asyncio` extension's engine and session.

#### Virtual currencies

The first feature I planned was CRUD backed by sqlite for virtual currencies through bot commands. The idea is to boost positive engagement with virtual currencies. E.g. I wanted there to be a way 

Following that, I needed a way to account for the creation and spending of these virtual currencies and their exchange.

Specifally, I needed
- sources/incomes for currencies
- a mechanism for their exchange at rates determined in some way
- sinks to make desirable.

I was not able to work on all these in the time I had but I was able to model some of these features. Specifically,
- A rewards system for income (Possibly in separate virtual currencies to incentivize different behaviors)
- An incomplete exchange market where currency exchange rates vary with demand/supply from users (Based on the market in Age of Empires and OffWorld trading company) 
- Virtual currency gambling games (Single/multiplayer and interactive or single round) to act as sinks
- I wanted to implement exclusive unlocking of emojis or the ability to set pins on channels (sort of ad billboards) with specicfic currencies (to keep their demand up relatively) but didn't have the time

#### Parsing and DSL

I found a great set of tutorials on parsing and language design [here](https://tomassetti.me/) (see references at the end).

And, I had a lot of fun trying to apply these concepts here.

I wrote two custom `pyleri` grammars to parse (what I'm calling):

##### Currency spec strings
E.g. define a currency UsDollar identified by the symbol 'USD' that has denominations of a grand, a buck, a quarter and a penny with a short description:

```currency SchruteBuck SB; description "For Office Motivation"; denominations: grand 1000, schrutebuck 1, quarter 0.25, penny 0.01;```

Parsing and storing these allows me to parse:

##### Currency amount strings

E.g. define currency amounts for 1009.26 

`1 grand, 9 schrutebuck, 1 quarter, 1 penny`

Allowing discord bot commands like:

```bp*guess_multi 1 grand, 9 schrutebuck, 1 quarter, 1 penny```

to start a multiplayer gambling game where all participants pay a 1009.26 buy in to play a guessing game for the combined pot.

Also, I wrote a prototype DSL to define reward policies. E.g, the following rule gives new guild members 10 schrute bucks for being greeting people in german in #general:

```
rule guten_tag
    event message send
    conditions [
        content *= 'guten tag' and channel__name == 'general'
    ]
    reward 1 BTC to author
end
```

# Concepts and Details


### Implemented Features and Commands

![Help msg](https://github.com/bk62/botter.py/raw/main/er_diagrams/screenshot.png)

#### Currency and economy admin

- `currency list` - list currencies in database. I wanted some currencies intended for specific purposes so four currencies, BotterPy BPY (base), RewardCoin RC (for rewards), GambleCoin GC etc added by init command.
- `currency add`, `currency edit` and `currency del` to add, update and delete
- `default` - Incomplete - Set defaults for specific channels etc - e.g. gamble with GambleCoin GC in games channels etc.
- `economy_status` - View Economy Status - only total money supply by currency, total amounts in wallets for now. (Intended to do hold more descriptive queries later.)
- `econ view_wallets` - view user wallets
- `econ deposit`, `econ withdraw` - deposit and withdraw from member wallets
- `econ transactions` - view and filter transaction logs i.e. payments, deposits, rewards etc - requires pagination/log downloads


#### User Wallet

- `wallet` - view currency balances in your wallet
- `pay`  - pay other users from your wallet
- `transactions` - view and filter your transaction logs - requires pagination/log downloads

#### Rewards admin/user
- `rewards show_policy`, `rewards download_policy`, `rewards update_policy` - view policy config file (detailed below in Parsing section), download it anad update it by uploading an edited file. Includes syntax validation but the errors are opaque.
- `rewards logs` - logs on who got rewarded how much for what reason by your policy
- `my_rewards` - users cana see their logs here

The last two need pagination or attachment downloade in order to get around discord filesize limits.


#### Gambling

- `cointoss` - simpls 50-50 gamble with virtual currency
- `guess_hilo` - a little bit compliccated (b/c cof asyncio) multi round guessing game with hints
- `guess_1p` - simple one player guessing game with dismally unfair odds
- `guess_multi` - quite complex multiplayer single round guessing game where players join by replying to the bot's game announcement, the closest guess wins the pot and pots are split between multiple winners


I think the last game is a good start to building complicated bot behavior reuiring multiple interactions with lots of users e.g. market mechanisms.

### Database

Here are the database schemas I used:

![Core discord models](https://github.com/bk62/botter.py/raw/main/er_diagrams/Core%20models.png)
Could use these models to implement multiple guild support, per channel settings, basic NLP (e.g. document similarity, word clouds etc). 

![Wallets and currencies](https://github.com/bk62/botter.py/raw/main/er_diagrams/Currency%20and%20wallets.png)

User wallets, currency speciications and transactions. 

![Rewards and exchange rates](https://github.com/bk62/botter.py/raw/main/er_diagrams/Transactions%20and%20logs.png)

I stored a lot of data in order to allow me to implement some sort of analytics. If put into practice, the concept of member run economies would probably need a lot of analysis and fiddling.

The currency exchange tables were implemented over a few hours and especially need more work.

### Parsing
An interesting to do with a discord bot is to figure out ways to use custom syntaxes and parsers to help make them more useful or more convenient. That is, something more complex than regular expressions and/or splitting on delimeters but less than analyzing natural language using ML algorithms or AI chatbots.

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

Having implemented currency spec and currency amount parsers, I needed a way to allow guild admins to reward members for various actions with their custom currencies. One way was to let them write their own `discord.py` event handlers and connect them to the `botter.py` database. The more fun way was to attempt to write a DSL to define reward policies in a text configuration file.

The idea here was to let guild admins define reward policies with a simple DSL -- intended more to be more of a proof of concept than to be expressive or execute efficiently.

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


Attributes like 'channel' and 'content' are added depending on the event and the context. Since this is a work in progress, the errors are opaque and there is no documentation -- I'll add them when I'm able to.

Here are a few more examples that don't all work:

```
// Reply in the help channel *or* reply with welcome anywhere
// Note: No parenthesis so left to right precedence
// multiple rewards
// Note: Fails
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
// Note: Fails
rule first_to_react_announcements
    event reaction add
    conditions [
        channel__name == 'announcements' and reaction__count == 1
    ]
    reward 3 btc to author
end

```
A policy document contains multiple rules. The `economy.cogs.rewards.Rewards` cog handles adding event listeners to enforce each rule.

Obvious deficiencies in the DSL are lack of comparisions, date parsing (e.g. for rules based on date since a user joined a server), more expressive conditionals, defining conditional names and referring to them in multiple rules (e.g. in_help_channel = channel__name == 'help') etc.


(The implementation of the DSL (using textx) is in `economy/rewards_dsl`.)


## Walkthrough

### 
 
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


I have been figuring out, through trial and error, the optimal code organization and API, so inefficient and buggy code co-exists with (relatively) well thought out code. I was focused more on implementing basic ideas *fast* than on optimal and efficient ways of doing things.

I'll be testing, improving, refactoring, rethinking pretty much all of the code in this project when I can.


- The currency exchange market feature is extremely rough and needs a lot of work
- Rewards DSL and its engine can be improved a lot assuming its something people would actually use
- The economy extension needs to follow the cog-service-repository-model architecture more closely
- Etc..

### Known issues

Lots of bug fixing, refactoring and rewriting needed as its being written by one person over a few days. 

But, the following will probably be on the backburner for a while:
- I have been testing on a private guild with only me as a member, so there are probably (but small and easily solvable) bugs with multiple users
- `bp*admin` extension reloading doesn't seem play well with econ ext. 
- Currency code and symbol attribute used inconsistently.
- Error handling is non-existent.
- I have created ORM models for guilds and channels but am not using them. And, since I'm using replitdb in a simplistic way to store defaults, needs work before using in multiple servers.
- and many more

## References

+ `basic-discord-bot` ([github](https://github.com/bk62/basic-discord-bot), [replit](https://replit.com/@bk62/Basic-Discord-Bot?v=1)) 
+ https://discordpy.readthedocs.io/en/latest
+ https://docs.sqlalchemy.org/


+ https://www.freecodecamp.org/news/create-a-discord-bot-with-python/
+ https://replit.com/@templates/Discordpy-bot-template-with-commands-extension
+ https://github.com/Rapptz/discord.py/tree/v1.7.2/examples 
+ https://tomassetti.me/quick-domain-specific-languages-in-python-with-textx/
+ https://textx.github.io/textX/stable/tutorials/

## License
[MIT](https://choosealicense.com/licenses/mit/)