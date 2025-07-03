import os
import re
from z3 import *
def import_instances(folder):
    def sorted_alphanumeric(data):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(data, key=alphanum_key)

    instances = []
    files = sorted_alphanumeric(os.listdir(folder))

    files = [f for f in files if f.endswith('.txt')]

    print(f"Loading instances: {files}")
    for file in files:
        with open(os.path.join(folder, file), 'r') as f:
            content = f.readlines()
            content = [x.strip() for x in content]
            instances.append(content)
    return instances


def get_parameters_from_instance(instance):
    n = int(instance[0])
    if n % 2 != 0:
        raise ValueError("Number of teams (n) must be even")
    weeks = n - 1
    periods = n // 2
    return n, weeks, periods

def z3_lex_less_eq(x, y, n, msg=None):
    if n == 0:
        return True
    return Or(
        And(x[0] == y[0], z3_lex_less_eq(x[1:], y[1:], n - 1, msg)),
        And(Not(x[0]), y[0])
    )