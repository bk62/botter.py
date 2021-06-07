import logging

import discord
from discord.ext import commands
from sqlalchemy.exc import SQLAlchemyError

import db
from base import BaseCog
from util import render_template
from economy import rewards_policy
from economy.cogs import Wallet
from economy import models


logger = logging.getLogger('economy.rewards.RewardsCog')


class Rewards(BaseCog, name='Economy.Rewards', description="Rewards in virtual currencies."):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.policy_engine = rewards_policy.RewardsPolicyEngine(service=self.service, bot=self.bot.command_prefix)

    def init_policy(self):
        for evt_handler, rule_event in self.policy_engine.interpret_policy():
            logger.debug(f'Adding event handler {rule_event.discord_event_name} for rule {rule_event.rule_name}')
            self.bot.add_listener(evt_handler, rule_event.discord_event_name)

    @commands.group(
        help='Rewards admin. Bot owner only. Stub'
    )
    async def rewards(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.rewards)
    
    @rewards.command(
        name='show_policy',
        help='View rewards policy. Bot owner only. Stub.'
    )
    async def rewards_show_policy(self, ctx):
        policy_text = rewards_policy.policy_file_content()
        data = dict(title='Reward Policy', text=policy_text)
        text = await render_template('reward_policy.jinja2', data)
        await ctx.reply(text)
    
    @rewards.command(
        name='download_policy',
        help='Download policy config file. Bot owner only.'
    )
    async def rewards_download_policy(self, ctx):
        pass
    
    @rewards.command(
        name='update_policy',
        help='Update rewards policy. Use download_policy command to download config file. Modify and upload using this command. Bot owner only. Stub.'
    )
    async def rewards_policy_update(self, ctx):
        pass
    
