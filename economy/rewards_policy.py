from pathlib import Path
import os
from dataclasses import dataclass
import logging

import discord
from textx import metamodel_from_file

DSL_PATH = Path(__file__).parent / 'rewards_dsl'

logger = logging.getLogger('economy.rewards.reward_policy')

# meta model
rewards_policy_mm = metamodel_from_file(str(DSL_PATH / 'reward.tx'))
# model
rewards_policy_m = rewards_policy_mm.model_from_file(DSL_PATH / 'reward_policy.rew')



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


@dataclass
class EventContext:
    """Event context dataclass."""

    rule_name: str = None

    event: str = None
    event_name: str = None
    event_type: str = None

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
    async def create(cls, rule_name, event, event_name, event_type, *args, **kwargs):
        logger.debug(f'Creating context for rule {rule_name}, event {event} ({event_name}-{event_type}) with args {args} and kwargs {kwargs}')

        ctx = cls(rule_name=rule_name, event=event, event_name=event_name, event_type=event_type)
        if event == 'on_message':
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
        elif event == 'on_member_join':
            ctx.member = args[0]
        elif event == 'on_reaction_add':
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

        event = EVENTS[rule.event.name][rule.event.type]
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
