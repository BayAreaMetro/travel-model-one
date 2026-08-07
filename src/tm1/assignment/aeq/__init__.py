"""AequilibraE open-source assignment backend (Task 2).

Reproduces the Cube highway/transit assignment for functional-parity evaluation:
network import (Cube net -> AequilibraE graph), the custom VDF, multi-class
equilibrium assignment, skimming, and transit.
"""

from tm1.assignment.aeq.runner import run_assignment_iteration

__all__ = ["run_assignment_iteration"]
