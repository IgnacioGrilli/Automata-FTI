import os
from collections import defaultdict
from typing import Dict, Set

EPSILON_SYMBOLS = {'', 'ε', 'eps', 'epsilon'}

class Automaton:
    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        start_state: str,
        accept_states: Set[str],
        transitions: Dict[str, Dict[str, Set[str]]],
        is_dfa: bool = False,
        name: str = 'automaton',
        state_composition: Dict[str, Set[str]] = None,
    ):
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.start_state = start_state
        self.accept_states = set(accept_states)
        self.transitions = transitions
        self.is_dfa = is_dfa
        self.name = name
        self.state_composition = state_composition or {}

    def copy(self) -> 'Automaton':
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
            state_composition=dict(self.state_composition),
        )

    def get_readable_state_name(self, state: str) -> str:
        if state in self.state_composition:
            composition = sorted(self.state_composition[state])
            if len(composition) > 1:
                return f"{state}<{','.join(composition)}>"
            elif len(composition) == 1:
                return f"{state}<{composition[0]}>"
        return state

    def get_stats(self) -> Dict:
        total_transitions = sum(
            len(dests)
            for state_trans in self.transitions.values()
            for dests in state_trans.values()
        )
        epsilon_transitions = sum(
            len(dests)
            for state_trans in self.transitions.values()
            for symbol, dests in state_trans.items()
            if symbol in EPSILON_SYMBOLS
        )
        return {
            'states': len(self.states),
            'alphabet_size': len(self.alphabet),
            'accept_states': len(self.accept_states),
            'total_transitions': total_transitions,
            'epsilon_transitions': epsilon_transitions,
            'is_dfa': self.is_dfa
        }
