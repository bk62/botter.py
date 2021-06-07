from jinja2 import Environment, FileSystemLoader, select_autoescape
from discord.ext import commands

#
# Jinja2 templating:

def get_template_env(template_dir='templates'):
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(),
        enable_async=True
    )
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