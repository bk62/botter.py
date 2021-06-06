import discord
from discord.ext import commands

from util import render_template
from economy import rewards_policy
from economy.cogs import Wallet


class Rewards(commands.Cog, name='Economy: Rewards.'):
    def __init__(self, bot):
        self.bot = bot
        self.policy_model = rewards_policy.rewards_policy_m

    async def exec_reward(self, reward, ctx):
        print('executing reward')
        print(reward.user, ctx.get_attribute(reward.user))
        print(reward.currency_amount.amount, reward.currency_amount.code)

        wallet_cog: Wallet = self.bot.get_cog('Economy: Wallet and Payments.')

        # Let's assume Wallet cog is there! TODO
        # if wallet_cog is None:
        #     raise Exception('Cannot run Rewards cog without Wallet cog.')

        # ensure user has wallet
        user = ctx.get_attribute(reward.user)
        await wallet_cog.get_or_create_wallet_embed(user)
        # get currency amount from parsed string
        currency_str = f'{reward.currency_amount.amount} {reward.currency_amount.code}'
        currency_amount = await wallet_cog.currency_amount_from_str(currency_str)
        # deposit reward amount
        await wallet_cog.deposit_in_wallet(user.id, currency_amount.symbol, currency_amount.amount)

    def interpret_policy(self):
        policy_model = self.policy_model
        for rule in policy_model.rules:
            print(f'Interpreting policy rule {rule.name}')
            event_name, event_type = rule.event.name, rule.event.type
            event = rewards_policy.EVENTS[event_name][event_type]
            conditions = rule.conditions.statements if rule.conditions else []
            rewards = rule.rewards

            async def eval_conditions(event_context):
                print('eval')
                print(event_context)

                # equivalent to s1 OR s2 OR ...
                for statement in conditions:
                    val = rewards_policy.eval_statement(statement, event_context)
                    if val:
                        # short circuit
                        return True
                return False

            async def exec_rewards(event_context):
                for reward in rewards:
                    await self.exec_reward(reward, event_context)

            async def evt_handler(*args, **kwargs):
                event_context = await rewards_policy.EventContext.create(event, event_name, event_type, *args, **kwargs)
                if await eval_conditions(event_context):
                    print('cond true, calling reward exec')
                    await exec_rewards(event_context)
                else:
                    print('cond fail')

            print('adding evt handler ', event)
            self.bot.add_listener(evt_handler, event)

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
    
