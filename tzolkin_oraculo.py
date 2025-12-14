#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tzolkin_oraculo.py
Cálculo do Kin do dia + Oráculo (Destino, Análogo, Antípoda, Guia, Oculto)

Baseado no "CÁLCULO DE KIN — Correlação Votan 206 (UNIFICADO, Revisão 6)".
Regras principais (resumo):
- Âncora do Kin 206: 20/12/2012 (Enlaçador de Mundos, Tom 11 Espectral, Branco).
- Ajuste Hunab Ku: contar 29/02 entre as datas; subtrair se alvo > âncora,
  somar se alvo < âncora.
- Kin calculado em ciclo de 260 (mod 260).
- Tom: 1–13 (mod 13), Selo: 1–20 (mod 20), Cor pelo selo (mod 4).
- Oráculo: Análogo, Antípoda, Guia e Oculto conforme regras do documento.

Uso (terminal):
    python tzolkin_oraculo.py                # hoje (date.today())
    python tzolkin_oraculo.py 07/02/2019     # dd/mm/aaaa
    python tzolkin_oraculo.py 2019-02-07     # yyyy-mm-dd
    python tzolkin_oraculo.py 2019-02-07 --json

Obs.: Se você rodar isso em servidor, "hoje" depende do fuso horário da máquina.
"""

from __future__ import annotations

from datetime import date, datetime
import argparse
import json
import re
from typing import Dict, Any, Tuple


SEALS = [
    "Dragão", "Vento", "Noite", "Semente", "Serpente",
    "Enlaçador de Mundos", "Mão", "Estrela", "Lua", "Cão",
    "Macaco", "Humano", "Caminhante do Céu", "Mago", "Águia",
    "Guerreiro", "Terra", "Espelho", "Tempestade", "Sol",
]

TONES = [
    "Magnético", "Lunar", "Elétrico", "Autoexistente", "Harmônico",
    "Rítmico", "Ressonante", "Galáctico", "Solar", "Planetário",
    "Espectral", "Cristal", "Cósmico",
]

COLORS = ["Vermelho", "Branco", "Azul", "Amarelo"]

# Âncora consistente com a Revisão 6:
# A combinação "Kin 206" cai em 20/12/2012 (véspera de 21/12/2012).
ANCHOR_DATE = date(2012, 12, 20)
ANCHOR_KIN = 206


def _is_leap(year: int) -> bool:
    return (year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))


def _hunab_ku_adjust(anchor: date, target: date) -> int:
    """
    Conta quantos 29/02 existem entre as datas (exclui o menor, inclui o maior),
    e aplica o sinal:
      - se target > anchor: retorna -contagem (subtrai)
      - se target < anchor: retorna +contagem (soma)
      - se igual: 0
    """
    if target == anchor:
        return 0

    mn, mx = (anchor, target) if anchor < target else (target, anchor)

    count = 0
    for y in range(mn.year, mx.year + 1):
        if _is_leap(y):
            feb29 = date(y, 2, 29)
            if feb29 > mn and feb29 <= mx:
                count += 1

    return -count if target > anchor else count


def kin_from_date(d: date) -> Tuple[int, int, int, str]:
    """
    Retorna (kin, tom, selo, cor) para uma data.

    kin: 1..260
    tom: 1..13
    selo: 1..20
    cor: Vermelho/Branco/Azul/Amarelo
    """
    delta = (d - ANCHOR_DATE).days + _hunab_ku_adjust(ANCHOR_DATE, d)

    kin = ((delta + (ANCHOR_KIN - 1)) % 260) + 1
    tone = ((kin - 1) % 13) + 1
    seal = ((kin - 1) % 20) + 1
    color = COLORS[(seal - 1) % 4]

    return kin, tone, seal, color


def kin_from_seal_tone(seal: int, tone: int) -> int:
    """Acha o Kin (1..260) que tem (selo, tom)."""
    for k in range(1, 261):
        if ((k - 1) % 20) + 1 == seal and ((k - 1) % 13) + 1 == tone:
            return k
    raise ValueError(f"Combinação inválida selo={seal}, tom={tone}")


# Regras do Oráculo (Revisão 6)
def analog_seal(seal: int) -> int:
    """
    Regra usada na Revisão 6: pares análogos "somam 19" no ciclo 1–20.
    Implementação modular para retornar 1..20.
    """
    r = (19 - (seal % 20)) % 20
    return 20 if r == 0 else r


def antipode_seal(seal: int) -> int:
    """Antípoda: selo + 10 no ciclo 1–20."""
    return ((seal + 9) % 20) + 1


def occult_seal(seal: int) -> int:
    """Oculto: selos que somam 21 (no ciclo 1–20)."""
    r = (21 - (seal % 20)) % 20
    return 20 if r == 0 else r


def occult_tone(tone: int) -> int:
    """Tom oculto: 14 − tom (no ciclo 1–13)."""
    r = (14 - (tone % 13)) % 13
    return 13 if r == 0 else r


# Guia: Selo por Cor × Tom
GUIDE_INDEX_BY_TONE = {
    1: None,
    2: 4,
    3: 3,
    4: 2,
    5: 3,
    6: None,
    7: 2,
    8: 1,
    9: 0,
    10: 2,
    11: None,
    12: 1,
    13: 3,
}

COLOR_GROUPS = {
    "Vermelho": [1, 5, 9, 13, 17],
    "Branco":   [2, 6, 10, 14, 18],
    "Azul":     [3, 7, 11, 15, 19],
    "Amarelo":  [4, 8, 12, 16, 20],
}


def guide_seal(seal: int, tone: int) -> int:
    if tone in (1, 6, 11):
        return seal  # auto-guiado
    color = COLORS[(seal - 1) % 4]
    group = COLOR_GROUPS[color]
    return group[GUIDE_INDEX_BY_TONE[tone]]  # type: ignore[index]


def full_oracle_for_date(d: date) -> Dict[str, Any]:
    kin, tone, seal, color = kin_from_date(d)

    a_s = analog_seal(seal)
    an_s = antipode_seal(seal)
    g_s = guide_seal(seal, tone)
    o_s = occult_seal(seal)
    o_t = occult_tone(tone)

    def part(seal_num: int, tone_num: int) -> Dict[str, Any]:
        k = kin_from_seal_tone(seal_num, tone_num)
        return {
            "kin": k,
            "selo_num": seal_num,
            "selo_nome": SEALS[seal_num - 1],
            "tom_num": tone_num,
            "tom_nome": TONES[tone_num - 1],
            "cor": COLORS[(seal_num - 1) % 4],
        }

    return {
        "data": d.strftime("%d/%m/%Y"),
        "destino": {**part(seal, tone), "kin": kin, "cor": color},
        "analogo": part(a_s, tone),
        "antipoda": part(an_s, tone),
        "guia": part(g_s, tone),
        "oculto": part(o_s, o_t),
    }


def format_oracle(oracle: Dict[str, Any]) -> str:
    def fmt(label: str, key: str) -> str:
        p = oracle[key]
        return (
            f"- {label}: Kin {p['kin']} — "
            f"{p['selo_nome']} ({p['selo_num']}), "
            f"{p['tom_nome']} (Tom {p['tom_num']})"
        )

    return "\n".join(
        [
            f"Oráculo para {oracle['data']}",
            fmt("Destino", "destino"),
            fmt("Análogo", "analogo"),
            fmt("Antípoda", "antipoda"),
            fmt("Guia", "guia"),
            fmt("Oculto", "oculto"),
        ]
    )


def parse_date_arg(s: str) -> date:
    """
    Aceita:
    - DD/MM/AAAA
    - AAAA-MM-DD
    """
    s = s.strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
        return datetime.strptime(s, "%d/%m/%Y").date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.strptime(s, "%Y-%m-%d").date()
    raise ValueError("Data inválida. Use DD/MM/AAAA ou AAAA-MM-DD.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kin do dia + Oráculo (Revisão 6).")
    parser.add_argument("data", nargs="?", help="DD/MM/AAAA ou AAAA-MM-DD. Se vazio: hoje.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON ao invés de texto.")
    args = parser.parse_args()

    d = date.today() if not args.data else parse_date_arg(args.data)
    oracle = full_oracle_for_date(d)

    if args.json:
        print(json.dumps(oracle, ensure_ascii=False, indent=2))
    else:
        print(format_oracle(oracle))


if __name__ == "__main__":
    main()
