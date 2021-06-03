from discord.ext import commands
from replit import db
import random



def get_econ_key(member):
  return f'economy_{member.id}'

class Economy(commands.Cog, name='Economy'):

  def __init__(self, bot):
    self.bot = bot

  async def deposit_amount(self, member, amount):
    key = get_econ_key(member)
    if key not in db.keys():
      db[key] = amount
    else:
      db[key] += amount
    
  async def withdraw_amount(self, member, amount):
    key = get_econ_key(member)
    if key in db.keys() and amount >= db[key]:
      db[key] -= amount
   
  @commands.group(invoke_without_command=True)
  async def balance(self, ctx):
    key = get_econ_key(ctx.author)
    if key not in db.keys():
      db[key] = (0.0)
    await ctx.send(f'Your balance is {db[key]}')
  
  @balance.command()
  async def deposit(self, ctx, amount: float ):
    if len(ctx.message.mentions) < 1:
      await ctx.send(f'Invalid: You must specify users by mentioning them.')
      return
    for member in ctx.message.mentions:
      await self.deposit_amount(member, amount)
    await ctx.send(f'Deposited {amount}')
    
  @balance.command()
  async def withdraw(self, ctx, amount: float ):
    if len(ctx.message.mentions) < 1:
      await ctx.send(f'Invalid: You must specify users by mentioning them.')
      return
    for member in ctx.message.mentions:
      await self.withdraw_amount(member, amount)
    await ctx.send(f'Withdrew {amount}')
 


class Gambling(commands.Cog, name='Gambling'):
  def __init__(self, bot):
      self.bot = bot

  def coinflip(self):
        return random.randint(0, 1)

  @commands.command()
  async def gamble(self, ctx, amount: float):
      """Gambles some money."""
      economy = self.bot.get_cog('Economy')
      won = False
      if economy is not None:
          await economy.withdraw_amount(ctx.author, amount)
          if self.coinflip() == 1:
              await economy.deposit_amount(ctx.author, amount * 1.5)
              won = True
      win_lose = f'won {amount * 1.5}!!!' if won else 'lost it all. Try again!'
      await ctx.send(f'You gambled {amount} and {win_lose}')



def setup(bot):
  bot.add_cog(Economy(bot))
  bot.add_cog(Gambling(bot))
