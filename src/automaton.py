from collections import defaultdict
from typing import Dict, Set


EPSILON_SYMBOLS = {"", "ε", "eps", "epsilon"}


class Automaton:
    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        start_state: str,
        accept_states: Set[str],
        transitions: Dict[str, Dict[str, Set[str]]],
        is_dfa: bool = False,
        name: str = "automaton",
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
            "states": len(self.states),
            "alphabet_size": len(self.alphabet),
            "accept_states": len(self.accept_states),
            "total_transitions": total_transitions,
            "epsilon_transitions": epsilon_transitions,
            "is_dfa": self.is_dfa,
        }

    def validate_string(self, input_str: str) -> bool:
        if self.is_dfa:
            current_state = self.start_state

            for symbol in input_str:
                if symbol not in self.alphabet:
                    return False
                transitions = self.transitions.get(current_state, {})
                dests = transitions.get(symbol)
                if not dests:
                    return False
                current_state = next(iter(dests))

            return current_state in self.accept_states
        else:
            # NFA con épsilon: BFS con cierre épsilon
            def epsilon_closure(states):
                closure = set(states)
                stack = list(states)

                while stack:
                    state = stack.pop()
                    for eps in EPSILON_SYMBOLS:
                        for next_state in self.transitions.get(state, {}).get(eps, []):
                            if next_state not in closure:
                                closure.add(next_state)
                                stack.append(next_state)

                return closure

            current_states = epsilon_closure({self.start_state})

            for symbol in input_str:
                next_states = set()

                for state in current_states:
                    for dest in self.transitions.get(state, {}).get(symbol, []):
                        next_states.add(dest)

                current_states = epsilon_closure(next_states)

            return any(state in self.accept_states for state in current_states)
