import re
from tabulate import tabulate

# =========================
# KEYWORDS
# =========================
keywords = {'BEGIN', 'PRINT', 'INTEGER', 'REAL', 'STRING', 'FOR', 'TO', 'END'}

# =========================
# TOKEN SPECIFICATION
# =========================
token_specification = [
    ('KEYWORD',  r'\b(?:BEGIN|PRINT|INTEGER|REAL|STRING|FOR|TO|END)\b'),
    ('NUMBER', r'-?\d+\.?\d*(?:[Ee][+-]?\d+)?'),
    ('STRING', r'"[^"]*"'),
    ('IDENTIFIER', r'\b[a-zA-Z_]\w*\b'),
    ('ASSIGN', r':='),
    ('SEMICOLON', r';'),
    ('COMMA', r','),
    ('NEWLINE', r'\n'),
    ('SKIP', r'[ \t]+'),
    ('MISMATCH', r'.'),
]

tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)

# =========================
# SAMPLE INPUT
# =========================
source_code = """
BEGIN
PRINT "HELLO";
INTEGER A, B;
A := 5;
B := 10;
FOR I := 1 TO 3
PRINT A;
END
END
"""

# =========================
# TOKENIZATION
# =========================
tokens = []
token_values = {}
token_id = 1

keywords_set = set()
identifiers_set = set()
literals_set = set()

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

    tokens.append((kind, value))

    if kind == 'KEYWORD':
        keywords_set.add(value)
    elif kind == 'IDENTIFIER':
        identifiers_set.add(value)
    elif kind in ['NUMBER', 'STRING']:
        literals_set.add(value)

# Add end marker
tokens.append(('$', '$'))

# =========================
# SYMBOL TABLES
# =========================
symbol_keywords = [[k] for k in sorted(keywords_set)]
symbol_identifiers = [[i] for i in sorted(identifiers_set)]
symbol_literals = [[l] for l in sorted(literals_set)]

# =========================
# LL(1) PARSER
# =========================

# Grammar rules (dictionary form)
grammar = {
    "program": [["BEGIN", "stmt_list", "END"]],
    "stmt_list": [["stmt", "stmt_list"], ["ε"]],
    "stmt": [["PRINT", "expr", "SEMICOLON"],
             ["declaration"],
             ["assignment"],
             ["for_loop"]],
    "declaration": [["type", "var_list", "SEMICOLON"]],
    "type": [["INTEGER"], ["REAL"], ["STRING"]],
    "var_list": [["IDENTIFIER", "var_list_tail"]],
    "var_list_tail": [["COMMA", "IDENTIFIER", "var_list_tail"], ["ε"]],
    "assignment": [["IDENTIFIER", "ASSIGN", "expr", "SEMICOLON"]],
    "for_loop": [["FOR", "IDENTIFIER", "ASSIGN", "expr", "TO", "expr", "stmt_list", "END"]],
    "expr": [["IDENTIFIER"], ["NUMBER"], ["STRING"]],
}

# Terminal mapping
def get_token_type(token):
    kind, value = token
    if kind == 'KEYWORD':
        return value
    elif kind == 'IDENTIFIER':
        return "IDENTIFIER"
    elif kind == 'NUMBER':
        return "NUMBER"
    elif kind == 'STRING':
        return "STRING"
    elif kind == 'ASSIGN':
        return "ASSIGN"
    elif kind == 'SEMICOLON':
        return "SEMICOLON"
    elif kind == 'COMMA':
        return "COMMA"
    return value

# =========================
# PARSING FUNCTION
# =========================
def parse(tokens):
    stack = ["$", "program"]
    index = 0
    steps = []
    step_count = 1

    while stack:
        top = stack[-1]
        current_token = tokens[index]
        token_type = get_token_type(current_token)

        steps.append([step_count, " ".join(stack), token_type, ""])

        if top == token_type:
            stack.pop()
            index += 1
            steps[-1][3] = f"Match {token_type}"

        elif top == "$" and token_type == "$":
            steps[-1][3] = "Accept"
            break

        elif top in grammar:
            found_rule = None
            for production in grammar[top]:
                if production[0] == token_type or production[0] == "ε":
                    found_rule = production
                    break

            if not found_rule:
                steps[-1][3] = "Error"
                break

            stack.pop()
            if found_rule != ["ε"]:
                stack.extend(reversed(found_rule))

            steps[-1][3] = f"{top} → {' '.join(found_rule)}"

        else:
            steps[-1][3] = "Error"
            break

        step_count += 1

    return steps

# =========================
# RUN PARSER
# =========================
parsing_steps = parse(tokens)

# =========================
# OUTPUT
# =========================

print("\nTOKEN TABLE")
print(tabulate(tokens[:-1], headers=["Type", "Lexeme"], tablefmt="fancy_grid"))

print("\nSYMBOL TABLES")

print("\nKeywords")
print(tabulate(symbol_keywords, headers=["Keyword"], tablefmt="fancy_grid"))

print("\nIdentifiers")
print(tabulate(symbol_identifiers, headers=["Identifier"], tablefmt="fancy_grid"))

print("\nLiterals")
print(tabulate(symbol_literals, headers=["Literal"], tablefmt="fancy_grid"))

print("\nPARSING STEPS")
print(tabulate(parsing_steps,
               headers=["Step", "Stack", "Input", "Action"],
               tablefmt="grid"))

print("\nParsing completed!")
