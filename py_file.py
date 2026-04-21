import re
from tabulate import tabulate
from collections import defaultdict

# =========================
# LEXER
# =========================

keywords = {'BEGIN', 'PRINT', 'INTEGER', 'REAL', 'STRING', 'FOR', 'TO', 'END'}

token_specification = [
    ('KEYWORD',  r'\b(?:BEGIN|PRINT|INTEGER|REAL|STRING|FOR|TO|END)\b'),
    ('NUMBER', r'-?\d+\.?\d*(?:[Ee][+-]?\d+)?'),
    ('STRING', r'"[^"]*"'),
    ('IDENTIFIER', r'\b[a-zA-Z_]\w*\b'),
    ('OPERATOR',  r':=|;|,'),
    ('NEWLINE', r'\n'),
    ('SKIP', r'[ \t]+'),
    ('MISMATCH', r'.'),
]

tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)

# =========================
# INPUT (HARDCODED)
# =========================

source_code = """
BEGIN
PRINT "HELLO";
INTEGER A, B, C;
REAL D, E;
STRING X, Y;
A := 2;
B := 4;
C := 6;
D := -3.65E-8;
E := 4.567;
X := "text1";
Y := "hello there";
FOR I := 1 TO 5
PRINT "Strings are [X] and [Y]";
END
END
"""

# =========================
# TOKENIZATION
# =========================

tokens = []
token_stream = []
token_values = {}
token_id = 1

kw_set, id_set, lit_set = set(), set(), set()

for mo in re.finditer(tok_regex, source_code):
    kind = mo.lastgroup
    value = mo.group()

    if kind in ['SKIP', 'NEWLINE']:
        continue

    if kind == 'MISMATCH':
        raise RuntimeError(f"Unexpected token: {value}")

    if kind == 'IDENTIFIER' and value in keywords:
        kind = 'KEYWORD'

    if value not in token_values:
        token_values[value] = token_id
        token_id += 1

    tokens.append((kind, value, token_values[value]))

    # Normalize tokens for parser
    if kind == 'IDENTIFIER':
        token_stream.append('IDENTIFIER')
        id_set.add(value)
    elif kind == 'NUMBER':
        token_stream.append('NUMBER')
        lit_set.add(value)
    elif kind == 'STRING':
        token_stream.append('STRING')
        lit_set.add(value)
    else:
        token_stream.append(value)
        if kind == 'KEYWORD':
            kw_set.add(value)

token_stream.append('$')

# =========================
# GRAMMAR
# =========================

grammar = {
    "program": [["BEGIN", "stmt_list", "END"]],
    "stmt_list": [["stmt", "stmt_list"], ["ε"]],
    "stmt": [["PRINT", "expr", ";"], ["declaration"], ["assignment"], ["for_loop"]],
    "declaration": [["type", "var_list", ";"]],
    "type": [["INTEGER"], ["REAL"], ["STRING"]],
    "var_list": [["IDENTIFIER", "var_list_tail"]],
    "var_list_tail": [[",", "IDENTIFIER", "var_list_tail"], ["ε"]],
    "assignment": [["IDENTIFIER", ":=", "expr", ";"]],
    "for_loop": [["FOR", "IDENTIFIER", ":=", "expr", "TO", "expr", "stmt_list", "END"]],
    "expr": [["IDENTIFIER"], ["NUMBER"], ["STRING"]]
}

non_terminals = list(grammar.keys())
terminals = set()

for head, prods in grammar.items():
    for prod in prods:
        for sym in prod:
            if sym not in grammar and sym != "ε":
                terminals.add(sym)

terminals.add('$')

# =========================
# FIRST SET
# =========================

FIRST = defaultdict(set)

def first(symbol):
    if symbol in terminals:
        return {symbol}
    result = set()
    for prod in grammar[symbol]:
        if prod[0] == "ε":
            result.add("ε")
        else:
            for sym in prod:
                f = first(sym)
                result |= (f - {"ε"})
                if "ε" not in f:
                    break
            else:
                result.add("ε")
    return result

for nt in non_terminals:
    FIRST[nt] = first(nt)

# =========================
# FOLLOW SET
# =========================

FOLLOW = defaultdict(set)
FOLLOW["program"].add('$')

changed = True
while changed:
    changed = False
    for head, prods in grammar.items():
        for prod in prods:
            for i, B in enumerate(prod):
                if B in non_terminals:
                    beta = prod[i+1:]
                    if beta:
                        first_beta = set()
                        for sym in beta:
                            first_beta |= (first(sym) - {"ε"})
                            if "ε" not in first(sym):
                                break
                        else:
                            first_beta.add("ε")

                        before = len(FOLLOW[B])
                        FOLLOW[B] |= (first_beta - {"ε"})
                        if "ε" in first_beta:
                            FOLLOW[B] |= FOLLOW[head]
                        if len(FOLLOW[B]) > before:
                            changed = True
                    else:
                        before = len(FOLLOW[B])
                        FOLLOW[B] |= FOLLOW[head]
                        if len(FOLLOW[B]) > before:
                            changed = True

# =========================
# PARSING TABLE
# =========================

parsing_table = defaultdict(dict)

for head, prods in grammar.items():
    for prod in prods:
        first_set = set()
        if prod[0] == "ε":
            first_set.add("ε")
        else:
            for sym in prod:
                first_set |= (first(sym) - {"ε"})
                if "ε" not in first(sym):
                    break
            else:
                first_set.add("ε")

        for t in first_set - {"ε"}:
            parsing_table[head][t] = prod

        if "ε" in first_set:
            for t in FOLLOW[head]:
                parsing_table[head][t] = prod

# =========================
# LL(1) PARSER
# =========================

stack = ["$", "program"]
input_ptr = 0

actions = []
step = 1

while stack:
    top = stack[-1]
    current = token_stream[input_ptr]

    actions.append([step, " ".join(stack), current, ""])

    if top == current == "$":
        actions[-1][3] = "Accept"
        break

    elif top == current:
        stack.pop()
        input_ptr += 1
        actions[-1][3] = f"Match {current}"

    elif top in terminals:
        actions[-1][3] = "ERROR"
        break

    else:
        if current in parsing_table[top]:
            prod = parsing_table[top][current]
            stack.pop()
            if prod != ["ε"]:
                stack.extend(reversed(prod))
            actions[-1][3] = f"{top} -> {' '.join(prod)}"
        else:
            actions[-1][3] = "ERROR"
            break

    step += 1

# =========================
# OUTPUT
# =========================

print("\nTOKEN TABLE")
print(tabulate(tokens, headers=["Type", "Lexeme", "ID"], tablefmt="fancy_grid"))

print("\nSYMBOL TABLES")

print("\nKeywords")
print(tabulate([[k] for k in sorted(kw_set)], headers=["Keyword"], tablefmt="fancy_grid"))

print("\nIdentifiers")
print(tabulate([[i] for i in sorted(id_set)], headers=["Identifier"], tablefmt="fancy_grid"))

print("\nLiterals")
print(tabulate([[l] for l in sorted(lit_set)], headers=["Literal"], tablefmt="fancy_grid"))

print("\nGRAMMAR")
for k, v in grammar.items():
    for prod in v:
        print(f"{k} -> {' '.join(prod)}")

print("\nFIRST SETS")
print(tabulate([[k, ", ".join(FIRST[k])] for k in FIRST],
               headers=["Non-Terminal", "FIRST"], tablefmt="grid"))

print("\nFOLLOW SETS")
print(tabulate([[k, ", ".join(FOLLOW[k])] for k in FOLLOW],
               headers=["Non-Terminal", "FOLLOW"], tablefmt="grid"))

print("\nPARSING ACTIONS")
print(tabulate(actions,
               headers=["Step", "Stack", "Input", "Action"],
               tablefmt="grid"))

if actions[-1][3] == "Accept":
    print("\nParsing completed successfully!")
else:
    print("\nParsing failed!")
