# Reference: https://tomassetti.me/pyleri-tutorial/

from pyleri import (
    Grammar,
    Keyword,
    Regex,
    Sequence,
    List,
    Optional,
    Choice)
import re
import pprint
from dataclasses import dataclass

re_currency_name = '[a-zA-Z]+'
re_currency_symbol = '[a-zA-Z]{1,3}'  # TODO unicode
re_denom_name = '[a-zA-Z]+'
re_decimal_value = r'[0-9]*\.?[0-9]+'

CURRENCY_SPEC_DESC = """
                ```
                **Currency spec:**
                Use the following syntax:
                ```
                [currency] <name> <symbol>
                [description "Description in quotes."]
                [denominations: List of `<name> <value>` separated by ',']
                ```

                Add a semicolon or newlines between sections. A semicolon at the end is optional.
                Anything in square brackets [] are optional.

                Denominations are `<name> <value>` pairs separated by commas. Adding denominations means that the 
                bot parse currency strings like "1 grand, 1 USD and 2 dimes" in gambling or payment commands.
                
                Currency and denomination names cannot have spaces in them. Currency symbols should be 3 chars max.

                E.g.
                `currency HelpCoins HC; description "Get HelpCoins for answering questions. Use to unlock exclusive emojis.";`
                `Bitcoin BTC; description "The original cryptocurrency.";`
                `USDollar USD; denominations grand 1000, dime 0.10, penny 0.01;`
                """


class CurrencySpecGrammar(Grammar):
    k_currency = Keyword('currency', ign_case=True)
    r_name = Regex(re_currency_name)
    # k_symbol = Keyword('symbol', ign_case=True)
    r_symbol = Regex(re_currency_symbol)
    r_sep = Regex(r'[;\n\t\-\\\.]+')

    k_description = Keyword('description', ign_case=True)
    r_description = Regex('"([^"]*)"')

    k_denomination = Keyword('denominations', ign_case=True)
    r_denomination_name = Regex(re_denom_name)
    r_denomination_value = Regex(re_decimal_value)

    NAME = Sequence(Optional(k_currency), r_name, r_symbol, Optional(r_sep))
    DESCRIPTION = Sequence(k_description, r_description, Optional(r_sep))
    DENOMINATION = Sequence(r_denomination_name, r_denomination_value)
    DENOMINATIONS = Sequence(k_denomination, List(DENOMINATION, delimiter=','), Optional(r_sep))
    # SYMBOL = Sequence(k_symbol, r_symbol)

    START = Sequence(NAME, Optional(DESCRIPTION), Optional(DENOMINATIONS), )


class CurrencyAmountGrammar(Grammar):
    r_amount = Regex(re_decimal_value)
    r_symbol = Regex(re_currency_symbol)
    r_denomination_name = Regex(re_denom_name)

    CURRENCY = Sequence(r_amount, r_symbol)
    DENOMINATION = Sequence(r_amount, r_denomination_name)
    CURRENCY_OR_DENOM = Choice(CURRENCY, DENOMINATION)
    START = List(CURRENCY_OR_DENOM, delimiter=',')


class CurrencySyntaxError(SyntaxError):
    pass


class Parser:
    def __init__(self, string):
        self.string = string
        self._result = None
        self._grammar = None
        self._parsed_object = None

    def parse(self):
        self._result = self._grammar.parse(self.string)
        if not self._result.is_valid:
            raise CurrencySyntaxError('Could not parse spec: ' + self._result.as_str())  # TODO improve error msg
        self.parse_result_tree()
        return self._parsed_object

    def node_props(self, node, children):
        """Returns properties of a node object as a dictionary"""
        self.read_info(node)
        return {
            'start': node.start,
            'end': node.end,
            'name': node.element.name if hasattr(node.element, 'name') else None,
            'element': node.element.__class__.__name__,
            'string': node.string,
            'children': children}

    def get_children(self, children):
        """Recursive method to get the children of a node object"""
        return [self.node_props(c, self.get_children(c.children)) for c in children]

    def parse_result_tree(self):
        """visit all leaves of the tree"""
        start = self._result.tree.children[0] if self._result.tree.children else self._result.tree
        return self.node_props(start, self.get_children(start.children))

    def read_info(self, node):
        pass

    def pprint_parse_tree(self):
        pp = pprint.PrettyPrinter()
        pp.pprint(self.parse_result_tree())


class CurrencySpecParser(Parser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._grammar = CurrencySpecGrammar()
        self._parsed_object = self._currency = {}
        self._last_denom = None

    def read_info(self, node):
        self.update_currency(node)

    def update_currency(self, node):
        if hasattr(node.element, 'name'):
            if node.element.name == 'r_name':
                self._currency['name'] = node.string
            if node.element.name == 'r_symbol':
                self._currency['symbol'] = node.string
            if node.element.name == 'k_denomination':
                self._currency['denominations'] = {}
            if node.element.name == 'r_denomination_name':
                self._currency['denominations'][node.string] = None
                self._last_denom = node.string
            # TODO change denom val to val denom?
            if node.element.name == 'r_denomination_value':
                # b/c DFS in order
                if self._last_denom is None:
                    raise CurrencySyntaxError(
                        f'Denomination value {node.string} defined before name. ({node.start}:{node.end})')
                self._currency['denominations'][self._last_denom] = node.string
                self._last_denom = None
            if node.element.name == 'r_description':
                self._currency['description'] = node.string[1:-1]


@dataclass
class AmountItem:
    amount: str = None
    type: str = None
    is_denomination: str = None


class CurrencyAmountParser(Parser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._grammar = CurrencyAmountGrammar()
        self._parsed_object = self._amounts = []
        self._last_val = None

    def read_info(self, node):
        self.update_amounts(node)

    def update_amounts(self, node):
        if hasattr(node.element, 'name'):
            if node.element.name == 'r_amount':
                self._last_val = node.string
            if node.element.name == 'r_symbol' or node.element.name == 'r_denomination_name':
                if self._last_val is None:
                    raise CurrencySyntaxError(
                        f'Unmatched amount and symbol/denomination: {node.string} does not have an associated amount.'
                        f'({node.start}:{node.end})')
                a = AmountItem(amount=self._last_val, type=node.string, is_denomination=node.element.name == 'r_denomination_name')
                self._amounts.append(a)
