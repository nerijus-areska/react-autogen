from typing import Dict, List, Type
from app.workflows.base import BaseWorkflow


class WorkflowRegistry:
    _workflows: Dict[str, Type[BaseWorkflow]] = {}

    @classmethod
    def register(cls, workflow_class: Type[BaseWorkflow]):
        """Decorator for registration"""
        cls._workflows[workflow_class.name] = workflow_class
        return workflow_class

    @classmethod
    def get(cls, name: str) -> BaseWorkflow:
        """Get workflow instance by name"""
        if name not in cls._workflows:
            raise ValueError(f"Unknown workflow: {name}")
        return cls._workflows[name]()

    @classmethod
    def list_workflow_options(cls) -> List[dict]:
        """Return workflow metadata for router prompt (name, description, complexity_level)."""
        options = []
        for name, wf_class in cls._workflows.items():
            options.append({
                "name": name,
                "description": wf_class.description,
                "complexity_level": wf_class.complexity_level            })
        return options