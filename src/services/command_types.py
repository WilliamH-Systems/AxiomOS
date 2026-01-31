from enum import Enum


class CommandType(str, Enum):
    REMEMBER = "remember"
    RECALL = "recall"
    HELP = "help"
    CLEAR = "clear"
