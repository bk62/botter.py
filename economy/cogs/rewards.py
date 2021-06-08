import logging, os, typing

import discord
from discord.ext import commands
from sqlalchemy.exc import SQLAlchemyError

import db
from util import render_template
import settings
from economy import rewards_policy
from economy.cogs import Wallet
from economy import models
from .base import BaseEconomyCog



logger = logging.getLogger('economy.rewards.RewardsCog')


class Rewards(BaseEconomyCog, name='Economy.Rewards', description="Rewards in virtual currencies."):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.policy_engine = rewards_policy.RewardsPolicyEngine(service=self.service, bot=self.bot)

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
        file = rewards_policy.POLICY_FILE
        await ctx.reply('Please download and edit the policy config file below.', file=discord.File(file))

    
    @rewards.command(
        name='update_policy',
        help='Update rewards policy. Use download_policy command to download config file. Modify and upload using this command. Bot owner only. Stub.'
    )
    async def rewards_policy_update(self, ctx):
        if not settings.ENABLE_REWARDS_POLICY_FILE_UPLOAD:
            await self.reply_embed(ctx, 'Error', 'Policy file upload not enabled')
            return
        print(ctx.message.attachments)
        attachments = ctx.message.attachments
        if not attachments or len(attachments) != 1:
            await self.reply_embed(ctx, 'Error', 'Please upload the new policy file by itself.')
            return
        attachment = attachments[0]
        upload_path = rewards_policy.DSL_PATH / 'uploaded_policy_file.rew'
        try:
            await attachment.save(upload_path)
            valid, e = rewards_policy.validate_policy_file(upload_path)
            if not valid:
                raise e
        except Exception as e:
            if settings.DEBUG and ctx.author.id == self.bot.author_id:
                fields = [dict(name='Error message', value=str(e), inline=False)]
            await self.reply_embed(ctx, 'Error', 'Uploaded policy file is not valid.', fields=fields)
            os.remove(upload_path)
            return
        await self.reply_embed(ctx, 'Sucess', 'New policy file was uploaded. Now you just have to run `./run.py replace_policy_file` and restart the bot for the new policy to take effect.')
    

    @rewards.command(
        name='logs',
        help='View rewards logs. Filter by currencies and/or members.',
        usage="<@member mentions> <currency_symbol>",
        alias="reward_logs"
    )
    async def logs(self, ctx, members: commands.Greedy[discord.Member] = None, *, currency_str: typing.Optional[str] = None):
        if isinstance(members, discord.Member):
            # only one member
            members = [members]
        member_ids = None
        if members and len(members) > 0:
            member_ids = [member.id for member in members]
        currency_symbols = None
        if currency_str:
            currency_symbols = [
                c.strip() for c in currency_str.split()
            ]
        find_all = self.service.wallet_repo.find_rewards_by(member_ids, currency_symbols)
        logs = await self.service(find_all)
        
        if len(logs) < 1:
            await self.reply_embed(ctx, 'Error', 'No reward logs in database')
            return

        data = dict(title=f'Reward logs\n\n[{len(logs)} results filtered by member id in {member_ids}, currency symbol in {currency_symbols}]', object_list=logs)
        text = await render_template('base_list.txt.jinja2', data)
        await ctx.reply(text)
    
    @commands.command(
        name='my_rewards',
        help='View your reward logs. Filter by currencies.',
        usage="<currency_symbol>",
    )
    async def my_rewards(self, ctx, *, currency_str: typing.Optional[str] = None):
        currency_symbols = None
        if currency_str:
            currency_symbols = [
                c.strip() for c in currency_str.split()
            ]
        find_all = self.service.wallet_repo.find_user_rewards(ctx.author.id, currency_symbols)
        logs = await self.service(find_all)
        
        if len(logs) < 1:
            await self.reply_embed(ctx, 'Error', 'No reward logs in database')
            return

        data = dict(title=f'Reward logs\n\n[{len(logs)} results filtered by currency symbol in {currency_symbols}]', object_list=logs)
        text = await render_template('base_list.txt.jinja2', data)
        await ctx.reply(text)