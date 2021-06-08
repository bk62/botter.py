from pathlib import Path
import os
from dataclasses import dataclass
import logging

import discord
from textx import metamodel_from_file





DSL_PATH = Path(__file__).parent / 'rewards_dsl'
TX_FILE = str(DSL_PATH / 'reward.tx')
POLICY_FILE = DSL_PATH / 'reward_policy.rew'

logger = logging.getLogger('economy.rewards.reward_policy')

# meta model
rewards_policy_mm = metamodel_from_file(TX_FILE)
# model
rewards_policy_m = rewards_policy_mm.model_from_file(POLICY_FILE)


def validate_policy_file(fpath):
    try:
        rewards_policy_mm.model_from_file(fpath)
        return True, None
    except Exception as e:
        return False, e

@dataclass
class RewardRuleEvent:
    # event_name -> event_type -> discord.py event name
    # TODO replace with on_raw_* event where appropriate
    # TODO intents
    EVENTS = {
        'member': {
            'join': 'on_member_join',
            'leave': 'on_member_remove',
            'ban': 'on_member_ban',
            'unban': 'on_member_unban',
            'update': 'on_member_update',
        },
        'message': {
            'send': 'on_message',
            'edit': 'on_message_edit',
            'delete': 'on_message_delete',
        },
        'reaction': {
            'add': 'on_reaction_add',
            'remove': 'on_reaction_remove',
            'clear': 'on_reaction_clear',
        }
    }

    event_name: str
    event_type: str
    discord_event_name: str
    rule_name: str

    @classmethod
    def create(cls, rule_name, event_name, event_type):
        discord_event_name = cls.EVENTS[event_name][event_type]
        return cls(rule_name=rule_name, event_name=event_name, event_type=event_type, discord_event_name=discord_event_name)
    
    def __repr__(self):
        return f'RewardRuleEvent({self.rule_name!r}, {self.discord_event_name!r}, {self.event_name!r}, {self.event_type!r})'



@dataclass
class EventContext:
    """Event context dataclass."""

    rule_event: RewardRuleEvent = None

    member: discord.User = None

    message: discord.Message = None
    author: discord.User = None
    original_author: discord.User = None
    content: str = None
    channel: discord.TextChannel = None
    reply: bool = None
    original_message: discord.Message = None
    original_message_content: discord.Message = None

    reaction: discord.Reaction = None

    @classmethod
    async def create(cls, rule_event, *args, **kwargs):
        logger.debug(f'Creating context for {rule_event} with args {args} and kwargs {kwargs}')

        ctx = cls(rule_event=rule_event)
        if rule_event.discord_event_name == 'on_message':
            m = args[0]
            ctx.message = m
            ctx.author = m.author
            ctx.content = m.content
            ctx.channel = m.channel
            if m.reference is not None:
                ctx.reply = True
                if m.reference.cached_message:
                    ctx.original_message = m.reference.cached_message
                    ctx.original_author = m.reference.cached_message.author
                    ctx.original_message_content = m.reference.cached_message.content
        elif rule_event.discord_event_name == 'on_member_join':
            ctx.member = args[0]
        elif rule_event.discord_event_name == 'on_reaction_add':
            ctx.reaction = args[0]
            ctx.author = args[1]
            ctx.message = ctx.reaction.message
            ctx.original_author = ctx.message.author
            ctx.channel = ctx.message.channel
        
        logger.debug(f'Created context {ctx}')
        return ctx

    def get_attribute(self, attributes_str):
        """Use "__" to get nested attributes.

        eg.
        "message__author__id" returns self.message.author.id
        if self.message, self.message.author and self.message.author.id are not None.
        Returns None otherwise.
        """
        attributes = list(reversed(attributes_str.split('__')))
        val = getattr(self, attributes.pop(), None)
        while len(attributes) > 0:
            attr = attributes.pop()
            val = getattr(val, attr, None)
            if val is None:
                break
        if len(attributes) > 0:
            return None
        return val


class RewardsPolicyEngine:
    def __init__(self, service, bot):
        self.policy_model = rewards_policy_m
        self.service = service
        self.bot = bot
    
    def interpret_policy(self):
        policy_model = self.policy_model
        for rule in policy_model.rules:
            logger.debug(f'Interpreting policy rule {rule.name}')
            
            rule_event = RewardRuleEvent.create(rule.name, rule.event.name, rule.event.type)
            
            conditions = rule.conditions.statements if rule.conditions else []
            rewards = rule.rewards

            evt_handler = self.rule_event_handler( rule_event, conditions, rewards)
            yield evt_handler, rule_event
            # self.bot.add_listener(evt_handler, event)
    
    def rule_event_handler(self, rule_event: RewardRuleEvent, conditions, rewards):
        async def eval_conditions(event_context):
            logger.debug(f'Evaluating conditions for rule {rule_event.rule_name}')

            # equivalent to s1 OR s2 OR ...
            for statement in conditions:
                val = eval_statement(statement, event_context)
                if val:
                    # short circuit
                    return True
            return False

        async def exec_rewards(event_context):
            logger.debug(f'Executing reward_policy for rule {rule_event.rule_name}')
            for reward in rewards:
                await self.service.grant_reward(rule_event, event_context, reward)

        async def evt_handler(*args, **kwargs):
            logger.debug(f'Triggered event handler for {rule_event}')
            event_context = await EventContext.create(rule_event, *args, **kwargs)
            if rule_event.event_name == 'message' and event_context.message.content.startswith(self.bot.command_prefix):
                # skip commands to this bot # TODO possible to recog other bots?
                return
            if event_context.message.author == self.bot.user: # TODO check bot users?
                # skip msg from this bot
                return
            if await eval_conditions(event_context):
                await exec_rewards(event_context)

        return evt_handler



def print_policy(policy_model):
    for rule in policy_model.rules:
        print(f'Event {rule.event.name!r} {rule.event.type!r}')

        for statement in rule.conditions.statements:
            e = statement.firstExpr
            print(f'\t\t{e.notOp!r} {e.sub1!r} {e.op!r} {e.sub2!r}')
            for op, expr in zip(statement.operators, statement.exprs):
                print(f'\t\t{op}')
                e = expr
                print(f'\t\t{e.notOp!r} {e.sub1!r} {e.op!r} {e.sub2!r}')

        for reward in rule.rewards:
            print(f'{reward.currency_amount.amount!r} {reward.currency_amount.code!r} to {reward.user!r}')

        event = RewardRuleEvent.EVENTS[rule.event.name][rule.event.type]
        print(event)

def policy_file_content():
    with open(DSL_PATH / 'reward_policy.rew') as f:
        return f.read()


def eval_statement(stmt, ctx):
    """Evaluate a one or more expressions combined by and/or operators."""
    # TODO implement precedence parenthesis
    stmt_truth = eval_expr(stmt.firstExpr, ctx)
    for op, expr in zip(stmt.operators, stmt.exprs):
        if op == 'and':
            # and
            stmt_truth = stmt_truth and eval_expr(expr, ctx)
        else:
            # or
            stmt_truth = stmt_truth or eval_expr(expr, ctx)
    return stmt_truth


def eval_expr(expr, ctx):
    """Evaluate an expression containing (optionally negated) "subject operator subject" expressions.

    E.g. `content *= "sad"`
    I.e. content contains 'sad' substring.
    """
    expr_truth = True
    lhs = expr.sub1
    rhs = expr.sub2
    op = expr.op
    # if exp refers to a context attribute
    # resolve it
    if lhs.__class__.__name__ == 'Attribute':
        lhs = ctx.get_attribute(lhs.name)
    if rhs.__class__.__name__ == 'Attribute':
        rhs = ctx.get_attribute(rhs.name)
    if lhs is None or rhs is None:
        # if an attribute is not in context, condition
        # fails right away
        return False
    if op == '*=' or op == '~=' or op == '$=' or op == '^=':
        # if string match operator
        # typecast both sides to string
        # and convert to lowercase
        lhs = str(lhs).lower()
        rhs = str(rhs).lower()

    if op == '*=':
        # contains
        expr_truth = rhs in lhs
    elif op == '~=':
        # contains whitespace separated
        expr_truth = rhs in lhs.split()
    elif op == '^=':
        # starts with
        expr_truth = lhs.startswith(rhs)
    elif op == '$=':
        # ends with
        expr_truth = lhs.endswith(rhs)
    elif op == '|=':
        # exact match -- lower case
        expr_truth = lhs == rhs
    elif op == '==':
        expr_truth = rhs == lhs
    elif op == '!=':
        expr_truth = rhs != lhs

    # negate if needed
    if expr.notOp == 'not':
        expr_truth = not expr_truth
    return expr_truth
