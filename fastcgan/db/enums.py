from enum import Enum


class OutcomeStatus(Enum):
    planned = "Planned"
    started = "Just Started"
    progress = "In Progress"
    final = "Final Stages"
    complete = "Completed"
    dropped = "Dropped/Stoped"
