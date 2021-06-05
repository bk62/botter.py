from jinja2 import Environment, FileSystemLoader, select_autoescape


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