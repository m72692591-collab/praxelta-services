"""Typed source of truth for the Electric Atelier design tokens."""
from typing import Final, TypedDict

class TokenSet(TypedDict):
    colors: dict[str, str]
    radii: dict[str, str]
    space: dict[str, str]
    motion: dict[str, str]

TOKENS: Final[TokenSet] = {
    "colors": {"night":"#050A1B","deep":"#07112A","surface":"#0C1734","raised":"#111F43","white":"#F7FAFF","muted":"#AFC0DF","blue":"#1C7DFF","cyan":"#28E7F7","violet":"#7A42FF","magenta":"#F33DDF","lime":"#BEFF3B","amber":"#FFCC5C","danger":"#FF6680"},
    "radii": {"sm":"10px","md":"16px","lg":"22px","xl":"30px","device":"38px"},
    "space": {"1":"4px","2":"8px","3":"12px","4":"16px","5":"20px","6":"24px"},
    "motion": {"fast":"120ms","screen":"250ms","confirm":"420ms"},
}
