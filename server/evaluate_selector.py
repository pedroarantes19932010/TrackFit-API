"""Compara o seletor com escolhas rotuladas pelo treinador, fora do banco do piloto."""
import argparse
import json
from pathlib import Path

from server.provider import choose_template


def evaluate(cases, mode):
    hits = 0
    for number, case in enumerate(cases, start=1):
        choices = case["candidates"]
        expected = case["expected"]
        ids = [c["id"] for c in choices]
        if len(set(ids)) != len(ids) or expected not in ids:
            raise ValueError(f"Caso {number}: confira os IDs e a escolha esperada.")
        result = choose_template(case["profile"], choices, mode)
        hits += result == expected
        print(f"Caso {number}: esperado={expected}, selecionado={result}")
    print(f"Concordância: {hits}/{len(cases)}")
    return hits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--provider", choices=("demo","openai"), default="demo",
                        help="openai envia uma solicitação à API por caso e pode gerar cobrança.")
    args = parser.parse_args()
    evaluate(json.loads(args.cases.read_text(encoding="utf-8")), args.provider)
