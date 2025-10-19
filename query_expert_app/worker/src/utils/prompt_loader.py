"""
Prompt loader utility for loading and rendering Jinja2 templates.
Located in worker/src/utils/ but loads templates from worker/src/prompts/
"""
import os
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Utility class for loading and rendering Jinja2 prompt templates.
    """
    
    def __init__(self, prompts_dir: str = None):
        """
        Initialize the prompt loader.
        
        Args:
            prompts_dir: Path to the prompts directory. If None, uses default location.
        """
        if prompts_dir is None:
            # Default to worker/src/prompts directory
            # Navigate from utils directory to prompts directory
            current_file = Path(__file__)
            worker_src_dir = current_file.parent.parent  # Go up to worker/src
            prompts_dir = worker_src_dir / "prompts"
        
        self.prompts_dir = Path(prompts_dir)
        
        # Verify directory exists
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")
    
    def load_template(self, template_name: str) -> Template:
        """
        Load a Jinja2 template by name.
        
        Args:
            template_name: Name of the template file (e.g., 'agent_system.j2')
            
        Returns:
            Jinja2 Template object
        """
        try:
            template = self.env.get_template(template_name)
            logger.debug(f"Loaded template: {template_name}")
            return template
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {str(e)}")
            raise
    
    def render(self, template_name: str, **kwargs: Any) -> str:
        """
        Load and render a template with the provided variables.
        
        Args:
            template_name: Name of the template file
            **kwargs: Variables to pass to the template
            
        Returns:
            Rendered template as string
        """
        template = self.load_template(template_name)
        rendered = template.render(**kwargs)
        logger.debug(f"Rendered template: {template_name}")
        return rendered
    
    def render_from_string(self, template_string: str, **kwargs: Any) -> str:
        """
        Render a template from a string (useful for dynamic templates).
        
        Args:
            template_string: Template content as string
            **kwargs: Variables to pass to the template
            
        Returns:
            Rendered template as string
        """
        template = self.env.from_string(template_string)
        return template.render(**kwargs)


# Global prompt loader instance
_prompt_loader = None


def get_prompt_loader() -> PromptLoader:
    """
    Get the global prompt loader instance (singleton pattern).
    
    Returns:
        PromptLoader instance
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def load_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Convenience function to load and render a prompt template.
    
    Args:
        template_name: Name of the template file
        **kwargs: Variables to pass to the template
        
    Returns:
        Rendered prompt as string
    """
    loader = get_prompt_loader()
    return loader.render(template_name, **kwargs)