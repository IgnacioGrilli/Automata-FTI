import json
import os
from collections import defaultdict
from typing import Dict, Set
from automaton import Automaton, EPSILON_SYMBOLS


def parse_json_automaton(path: str) -> Automaton:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    states = set(data["states"])
    alphabet = set(data.get("alphabet", []))
    start_state = data["start_state"]
    accept_states = set(data["accept_states"])

    raw_trans = data.get("transitions", {})
    transitions: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    for s, symbol_map in raw_trans.items():
        for sym, dests in symbol_map.items():
            if isinstance(dests, str):
                dests = [dests]
            for d in dests:
                transitions[s][sym].add(d)
            if sym not in EPSILON_SYMBOLS:
                alphabet.add(sym)

    name = data.get("name", os.path.splitext(os.path.basename(path))[0])
    mentioned_states = set(transitions.keys())
    for s in list(transitions.keys()):
        for sym in transitions[s].keys():
            mentioned_states.update(transitions[s][sym])
    states |= mentioned_states

    is_dfa = all(
        (sym not in EPSILON_SYMBOLS) and len(dests) == 1
        for s in transitions
        for sym, dests in transitions[s].items()
    )

    return Automaton(states, alphabet, start_state, accept_states, transitions, is_dfa, name)


def automaton_to_json_dict(a: Automaton) -> dict:
    trans_dict = {}
    for s in sorted(a.states):
        sym_map = a.transitions.get(s, {})
        if not sym_map:
            continue
        out = {}
        for sym, dests in sym_map.items():
            if len(dests) == 1:
                out[sym] = sorted(dests)[0]
            else:
                out[sym] = sorted(dests)
        trans_dict[s] = out
    return {
        "name": a.name,
        "states": sorted(a.states),
        "alphabet": sorted(a.alphabet),
        "start_state": a.start_state,
        "accept_states": sorted(a.accept_states),
        "is_dfa": a.is_dfa,
        "transitions": trans_dict,
    }
