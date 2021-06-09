from jinja2 import Environment, FileSystemLoader, select_autoescape
from discord.ext import commands
import discord
from babel.dates import format_datetime

import settings

#
# Jinja2 templating:

def dt_format(value, format='short'):
    if format == 'long':
        format = "EEEE, d. MMMM y 'at' HH:mm"
    else:
        format = format="EE dd.MM.y HH:mm"
    return format_datetime(value, format)

def get_template_env(template_dir='templates'):
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(),
        enable_async=True,
        trim_blocks = True,
        lstrip_blocks = True
    )
    env.filters['dt_format'] = dt_format
    return env

def get_template(template):
    env = get_template_env('templates')
    return env.get_template(template)

async def render_template(template_name, template_context=None):
    if template_context is None:
        template_context = {}
    tmpl = get_template(template_name)
    text = await tmpl.render_async(**template_context)
    return text


#
# Misc 

def dump_command_ctx(ctx):
    attrs = {
        # name: inline
        'args': False,
        'kwargs': False,
        'command': True,
        'invoked_with': True,
        'invoked_subcommand': True,
        'subcommand_passed': True,
        'valid': True
    }
    for attr, inline in attrs.items():
        yield attr, getattr(ctx, attr, None), inline

def str_2_color(color):
    if color in settings.THEME:
        color = settings.THEME[color]
    color = getattr(discord.Colour, color, None)
    return color() if color else discord.Embed.Empty