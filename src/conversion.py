from typing import Set, Dict
from collections import defaultdict, deque
from automaton import Automaton, EPSILON_SYMBOLS


def epsilon_closure(
    state_set: Set[str], transitions: Dict[str, Dict[str, Set[str]]]
) -> Set[str]:
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


def move(
    state_set: Set[str], symbol: str, transitions: Dict[str, Dict[str, Set[str]]]
) -> Set[str]:
    result = set()

    for s in state_set:
        result |= transitions.get(s, {}).get(symbol, set())

    return result


def nfa_to_dfa(nfa: Automaton, name_suffix="__DFA") -> Automaton:
    if nfa.is_dfa and all(
        sym not in EPSILON_SYMBOLS
        for s in nfa.transitions
        for sym in nfa.transitions[s]
    ):
        dfa = nfa.copy()
        dfa.name = f"{dfa.name}{name_suffix}"
        return dfa

    alphabet = set([sym for sym in nfa.alphabet if sym not in EPSILON_SYMBOLS])
    start_closure = frozenset(
        sorted(epsilon_closure({nfa.start_state}, nfa.transitions))
    )

    state_name = {start_closure: "S0"}
    state_composition = {"S0": set(start_closure)}
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
                new_name = f"S{idx}"
                state_name[U_f] = new_name
                state_composition[new_name] = set(U_f)
                dfa_states.add(new_name)
                queue.append(U_f)
                if any(s in nfa.accept_states for s in U_f):
                    dfa_accepts.add(new_name)
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
        state_composition=state_composition,
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
            for a in dfa.alphabet
            if a in dfa.transitions.get(s, {})
        }
        for s in dfa.states
    }

    dfa.state_composition = {
        s: comp for s, comp in dfa.state_composition.items() if s in reachable
    }

    return dfa


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
    block_composition = {}

    for i, block in enumerate(P):
        name = f"M{i}"
        combined_composition = set()

        for s in block:
            block_names[s] = name
            if s in dfa.state_composition:
                combined_composition.update(dfa.state_composition[s])
            else:
                combined_composition.add(s)

        block_composition[name] = combined_composition

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
        state_composition=block_composition,
    )

    return minimized
