"""
Workflows package - contains all AI code modification workflow implementations.

Each workflow is a self-contained strategy for applying changes to a codebase.
Workflows are automatically registered when imported.
"""
from .base import BaseWorkflow
from .registry import WorkflowRegistry

# Import all workflow implementations
# This triggers their @WorkflowRegistry.register decorators
from .simple_modification import SimpleModificationWorkflow
from .explorative_modification import ExplorativeModificationWorkflow
# from .self_correcting import SelfCorrectingWorkflow  # Uncomment when implemented
# from .incremental import IncrementalWorkflow  # Uncomment when implemented


__all__ = [
    'BaseWorkflow',
    'WorkflowRegistry',
    'SimpleModificationWorkflow',
    'ExplorativeModificationWorkflow',
    # 'SelfCorrectingWorkflow',
    # 'IncrementalWorkflow',
]