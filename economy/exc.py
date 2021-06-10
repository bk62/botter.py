from discord.ext import commands



class WalletOpFailedException(commands.CommandError):
    pass


class NoMatchingCurrency(WalletOpFailedException):
    pass

class MultipleMatchingCurrencies(WalletOpFailedException):
    pass