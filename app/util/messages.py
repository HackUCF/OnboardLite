from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def load_and_render_template(template_path, **context):
    """
    Load a Jinja template from disk and render it with the provided context.

    Args:
        template_path: Path to the template file
        **context: Variables to pass to the template

    Returns:
        Rendered template as string
    """
    # Get the directory and filename
    template_dir = Path(template_path).parent
    template_name = Path(template_path).name

    # Create Jinja environment
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)

    # Render the template
    return template.render(**context)
