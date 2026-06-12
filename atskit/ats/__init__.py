from .base import ATSClient, JobModel
from . import (
    american_express,
    amazon,
    apple,
    ashby,
    gem,
    greenhouse,
    lever,
    microsoft,
    workday,
)

CLIENTS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "gem": gem,
    "workday": workday,
    "apple": apple,
    "amazon": amazon,
    "microsoft": microsoft,
    "american_express": american_express,
}

__all__ = [
    "ATSClient",
    "JobModel",
    "CLIENTS",
    "greenhouse",
    "lever",
    "ashby",
    "gem",
    "workday",
    "apple",
    "amazon",
    "microsoft",
    "american_express",
]
