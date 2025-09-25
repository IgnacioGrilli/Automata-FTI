#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nfa_dfa.py
----------
Lee un AFN (JSON, con o sin ε), lo convierte a AFD y opcionalmente lo minimiza (Hopcroft).
Uso:
  python nfa_dfa.py input.json
  python nfa_dfa.py input.json --no-minimize
  python nfa_dfa.py input.json -o salida.json --name MiAFD
"""

import json
import os
import sys
import argparse
from collections import defaultdict, deque
from typing import Dict, Set


# =====================
# Core automata classes
# =====================

EPSILON_SYMBOLS = {"", "ε", "eps", "epsilon"}


class Automaton:
    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        start_state: str,
        accept_states: Set[str],
        transitions: Dict[str, Dict[str, Set[str]]],  # state -> symbol -> set(dest)
        is_dfa: bool = False,
        name: str = "automaton",
    ):
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.start_state = start_state
        self.accept_states = set(accept_states)
        self.transitions = transitions  # NFA: set; DFA: singleton sets
        self.is_dfa = is_dfa
        self.name = name

    def copy(self) -> "Automaton":
        return Automaton(
            states=set(self.states),
            alphabet=set(self.alphabet),
            start_state=self.start_state,
            accept_states=set(self.accept_states),
            transitions={
                s: {a: set(dests) for a, dests in self.transitions.get(s, {}).items()}
                for s in self.states
            },
            is_dfa=self.is_dfa,
            name=self.name,
        )


# =====================
# Parsing / Serialization (JSON)
# =====================

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
    # Normalizar estados mencionados en transiciones
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


# =====================
# NFA -> DFA Conversion
# =====================

def epsilon_closure(state_set: Set[str], transitions: Dict[str, Dict[str, Set[str]]]) -> Set[str]:
    stack = list(state_set)
    closure = set(state_set)
    while stack:
        s = stack.pop()
        for eps_sym in EPSILON_SYMBOLS:
            for nxt in transitions.get(s, {}).get(eps_sym, set()):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)
    return closure


def move(state_set: Set[str], symbol: str, transitions: Dict[str, Dict[str, Set[str]]]) -> Set[str]:
    result = set()
    for s in state_set:
        result |= transitions.get(s, {}).get(symbol, set())
    return result


def nfa_to_dfa(nfa: Automaton, name_suffix="__DFA") -> Automaton:
    if nfa.is_dfa and all(sym not in EPSILON_SYMBOLS for s in nfa.transitions for sym in nfa.transitions[s]):
        dfa = nfa.copy()
        dfa.name = f"{dfa.name}{name_suffix}"
        return dfa

    alphabet = set([sym for sym in nfa.alphabet if sym not in EPSILON_SYMBOLS])

    start_closure = frozenset(sorted(epsilon_closure({nfa.start_state}, nfa.transitions)))
    state_name = {start_closure: "S0"}

    queue = deque([start_closure])
    dfa_states: Set[str] = {"S0"}
    dfa_trans: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    dfa_accepts: Set[str] = set()

    if any(s in nfa.accept_states for s in start_closure):
        dfa_accepts.add("S0")

    idx = 1
    while queue:
        T = queue.popleft()
        T_name = state_name[T]
        for a in alphabet:
            U = set()
            U |= move(set(T), a, nfa.transitions)
            U = epsilon_closure(U, nfa.transitions)
            U_f = frozenset(sorted(U))
            if not U_f:
                continue
            if U_f not in state_name:
                state_name[U_f] = f"S{idx}"
                dfa_states.add(state_name[U_f])
                queue.append(U_f)
                if any(s in nfa.accept_states for s in U_f):
                    dfa_accepts.add(state_name[U_f])
                idx += 1
            dfa_trans[T_name][a].add(state_name[U_f])

    for s in dfa_trans:
        for a in list(dfa_trans[s].keys()):
            dests = dfa_trans[s][a]
            if len(dests) > 1:
                dfa_trans[s][a] = {sorted(dests)[0]}

    dfa = Automaton(
        states=dfa_states,
        alphabet=alphabet,
        start_state="S0",
        accept_states=dfa_accepts,
        transitions=dfa_trans,
        is_dfa=True,
        name=f"{nfa.name}{name_suffix}",
    )
    dfa = remove_unreachable_states(dfa)
    return dfa


def remove_unreachable_states(dfa: Automaton) -> Automaton:
    reachable = set()
    stack = [dfa.start_state]
    while stack:
        s = stack.pop()
        if s in reachable:
            continue
        reachable.add(s)
        for a in dfa.alphabet:
            for d in dfa.transitions.get(s, {}).get(a, set()):
                if d not in reachable:
                    stack.append(d)
    dfa.states &= reachable
    dfa.accept_states &= reachable
    dfa.transitions = {
        s: {
            a: {d for d in dfa.transitions.get(s, {}).get(a, set()) if d in reachable}
            for a in dfa.alphabet if a in dfa.transitions.get(s, {})
        }
        for s in dfa.states
    }
    return dfa


# =====================
# DFA Minimization (Hopcroft)
# =====================

def hopcroft_minimize(dfa: Automaton, name_suffix="__MIN") -> Automaton:
    if not dfa.is_dfa:
        raise ValueError("hopcroft_minimize requiere un DFA")

    dfa = remove_unreachable_states(dfa)

    P = [set(dfa.accept_states), set(dfa.states - dfa.accept_states)]
    P = [p for p in P if p]

    from collections import deque as _deque
    W = _deque()
    if P:
        if len(P) == 2 and len(P[0]) > len(P[1]):
            W.append(P[1])
        else:
            W.append(P[0])

    def get_transition(state: str, symbol: str) -> str:
        dests = dfa.transitions.get(state, {}).get(symbol, set())
        return next(iter(dests), None)

    while W:
        A = W.popleft()
        for c in dfa.alphabet:
            X = set(s for s in dfa.states if get_transition(s, c) in A)
            new_P = []
            for Y in P:
                inter = Y & X
                diff = Y - X
                if inter and diff:
                    new_P.extend([inter, diff])
                    if Y in W:
                        W.remove(Y)
                        W.append(inter)
                        W.append(diff)
                    else:
                        if len(inter) <= len(diff):
                            W.append(inter)
                        else:
                            W.append(diff)
                else:
                    new_P.append(Y)
            P = new_P

    block_names = {}
    for i, block in enumerate(P):
        name = f"M{i}"
        for s in block:
            block_names[s] = name

    new_states = set(block_names.values())
    new_start = block_names[dfa.start_state]
    new_accepts = {block_names[s] for s in dfa.accept_states}

    new_trans: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    for s in dfa.states:
        s2 = block_names[s]
        for a in dfa.alphabet:
            d = next(iter(dfa.transitions.get(s, {}).get(a, set())), None)
            if d is not None:
                new_trans[s2][a].add(block_names[d])

    minimized = Automaton(
        states=new_states,
        alphabet=set(dfa.alphabet),
        start_state=new_start,
        accept_states=new_accepts,
        transitions=new_trans,
        is_dfa=True,
        name=f"{dfa.name}{name_suffix}",
    )
    return minimized


# =====================
# I/O Helpers & CLI
# =====================

def read_automaton(path: str) -> Automaton:
    return parse_json_automaton(path)


def write_automaton(a: Automaton, path: str) -> None:
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(automaton_to_json_dict(a), f, ensure_ascii=False, indent=2)


def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Convierte un AFN (JSON) a AFD y, opcionalmente, lo minimiza."
    )
    p.add_argument("input", help="Archivo de entrada (.json) con un AFN (ε permitido)")
    p.add_argument("-o", "--output", help="Archivo de salida (.json). Por defecto, junto a la entrada")
    p.add_argument("--no-minimize", action="store_true", help="No minimizar (emitir AFD crudo)")
    p.add_argument("--name", help="Nombre del autómata de salida")
    return p


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = build_arg_parser().parse_args(argv)

    a = read_automaton(args.input)

    dfa = nfa_to_dfa(a)
    out_auto = dfa if args.no_minimize else hopcroft_minimize(dfa)

    if args.name:
        out_auto.name = args.name

    out_path = args.output
    if not out_path:
        base, _ = os.path.splitext(args.input)
        suffix = "_dfa" if args.no_minimize else "_dfa_min"
        out_path = f"{base}{suffix}.json"

    write_automaton(out_auto, out_path)

    print(f"Input: {args.input} (json)  ->  Output: {out_path} (json)")
    print(f"States: {len(out_auto.states)} | Alphabet: {sorted(out_auto.alphabet)} | Start: {out_auto.start_state}")
    print(f"Accepting: {sorted(out_auto.accept_states)}")
    cnt = sum(len(v) for v in out_auto.transitions.values())
    print(f"Transitions (state->symbol edges): {cnt}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
