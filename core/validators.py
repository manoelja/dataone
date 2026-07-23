"""Validação e geração de documentos (CPF/CNPJ)."""

import random
from typing import Final


__all__ = [
    "validar_cpf",
    "validar_cnpj",
    "gerar_cpf_valido",
    "gerar_cnpj_valido",
]


def validar_cpf(cpf: str) -> bool:
    """Valida um CPF verificando o formato e os dígitos verificadores."""
    cpf_limpo = "".join(filter(str.isdigit, str(cpf)))
    if len(cpf_limpo) != 11 or len(set(cpf_limpo)) == 1:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf_limpo[j]) * ((i + 1) - j) for j in range(i))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != int(cpf_limpo[i]):
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    """Valida um CNPJ verificando o formato e os dígitos verificadores."""
    cnpj_limpo = "".join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_limpo) != 14 or len(set(cnpj_limpo)) == 1:
        return False
    pesos1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma1 = sum(int(cnpj_limpo[i]) * pesos1[i] for i in range(12))
    resto1 = soma1 % 11
    digito1 = 0 if resto1 < 2 else 11 - resto1
    if int(cnpj_limpo[12]) != digito1:
        return False
    pesos2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma2 = sum(int(cnpj_limpo[i]) * pesos2[i] for i in range(13))
    resto2 = soma2 % 11
    digito2 = 0 if resto2 < 2 else 11 - resto2
    return int(cnpj_limpo[13]) == digito2


def gerar_cpf_valido() -> str:
    """Gera um CPF válido aleatório formatado."""
    nine_digits = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum((len(nine_digits) + 1 - i) * v for i, v in enumerate(nine_digits)) % 11
        nine_digits.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, nine_digits[0:3]))}.{''.join(map(str, nine_digits[3:6]))}.{''.join(map(str, nine_digits[6:9]))}-{''.join(map(str, nine_digits[9:11]))}"


def gerar_cnpj_valido() -> str:
    """Gera um CNPJ válido aleatório formatado."""
    cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for _ in range(2):
        pesos = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2) if len(cnpj) == 12 else (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        val = sum(pesos[i] * v for i, v in enumerate(cnpj)) % 11
        cnpj.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, cnpj[0:2]))}.{''.join(map(str, cnpj[2:5]))}.{''.join(map(str, cnpj[5:8]))}/{''.join(map(str, cnpj[8:12]))}-{''.join(map(str, cnpj[12:14]))}"
