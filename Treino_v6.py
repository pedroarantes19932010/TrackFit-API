"""Registro local de treinos. Execute: python Treino_v6.py (Python 3.10+)."""

import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Caminho fixo: o histórico fica ao lado deste script, não na pasta do terminal.
ARQUIVO_HISTORICO = Path(__file__).resolve().with_name("historico_treinos.json")
MAX_BYTES = 20 * 1024 * 1024
MAX_EXERCICIOS = 100
MAX_SERIES = 100
MAX_REPETICOES = 10000
MAX_PESO = Decimal("10000")


class ErroHistorico(ValueError):
    """O arquivo não pode ser interpretado com segurança."""


class HistoricoOcupado(OSError):
    """Outra execução está salvando no mesmo arquivo."""


def validar_texto(texto):
    texto = texto.strip()
    if not texto or len(texto) > 120 or any(not c.isprintable() for c in texto):
        raise ValueError("Digite um nome de 1 a 120 caracteres, sem caracteres de controle.")
    return texto


def converter_inteiro(texto, minimo, maximo):
    texto = texto.strip()
    if len(texto) > 10 or not re.fullmatch(r"[0-9]+", texto):
        raise ValueError("Digite apenas um número inteiro, sem letras ou decimais.")
    valor = int(texto)
    if not minimo <= valor <= maximo:
        raise ValueError(f"Digite um valor entre {minimo} e {maximo}.")
    return valor


def converter_peso(texto):
    texto = texto.strip()
    if len(texto) > 20 or not re.fullmatch(r"[0-9]+(?:[.,][0-9]{1,3})?", texto):
        raise ValueError("Use, por exemplo, 12,5 ou 12.5, sem unidade ou separador de milhar.")
    peso = Decimal(texto.replace(",", "."))
    if not Decimal("0") <= peso <= MAX_PESO:
        raise ValueError(f"A carga deve estar entre 0 e {MAX_PESO} kg.")
    return peso


def perguntar(mensagem, conversor):
    """Repete somente a pergunta inválida. Ctrl+C cancela o registro."""
    while True:
        try:
            return conversor(input(mensagem))
        except ValueError as erro:
            print(f"Entrada inválida: {erro}")


def perguntar_sim_nao(mensagem):
    def converter(texto):
        resposta = texto.strip().casefold()
        if resposta in ("s", "sim"):
            return True
        if resposta in ("n", "nao", "não"):
            return False
        raise ValueError("Responda s ou n.")
    return perguntar(mensagem, converter)


def calcular_volume(series, repeticoes, peso):
    """Volume de carga externa; não representa trabalho mecânico ou esforço."""
    if type(series) is not int or not 1 <= series <= MAX_SERIES:
        raise ValueError("Quantidade de séries inválida.")
    if type(repeticoes) is not int or not 1 <= repeticoes <= MAX_REPETICOES:
        raise ValueError("Quantidade de repetições inválida.")
    carga = converter_peso(str(peso))
    return carga * series * repeticoes


def coletar_exercicio(numero):
    print(f"\n--- Exercício {numero} ---")
    nome = perguntar("Nome do exercício: ", validar_texto)
    quantidade = perguntar("Quantas séries? ", lambda t: converter_inteiro(t, 1, MAX_SERIES))
    iguais = quantidade == 1 or perguntar_sim_nao(
        "Mesma carga e repetições em todas as séries? (s/n): "
    )
    detalhes = []
    for indice in range(1 if iguais else quantidade):
        if not iguais:
            print(f"Série {indice + 1}:")
        peso = perguntar("Carga externa (kg; 0 se não houver): ", converter_peso)
        reps = perguntar("Repetições: ", lambda t: converter_inteiro(t, 1, MAX_REPETICOES))
        detalhes.append({"peso_kg": float(peso), "repeticoes": reps})
    if iguais:
        detalhes = [dict(detalhes[0]) for _ in range(quantidade)]
    volume = sum((calcular_volume(1, s["repeticoes"], s["peso_kg"])
                  for s in detalhes), Decimal("0"))
    exercicio = {
        "exercicio": nome,
        "series": quantidade,
        "series_detalhes": detalhes,
        "volume_total": float(volume),
    }
    if iguais:
        exercicio.update(detalhes[0])
    print(f"Volume de carga externa: {volume} kg")
    return exercicio


def coletar_sessao():
    aluno = perguntar("Nome do aluno: ", validar_texto)
    quantidade = perguntar("Quantos exercícios deseja registrar? ",
                           lambda t: converter_inteiro(t, 1, MAX_EXERCICIOS))
    inicio = datetime.now().astimezone().isoformat(timespec="seconds")
    exercicios = [coletar_exercicio(n) for n in range(1, quantidade + 1)]
    total = sum((Decimal(str(e["volume_total"])) for e in exercicios), Decimal("0"))
    return {
        "versao_formato": 2,
        "id": str(uuid4()),
        "registrado_em": inicio,
        "aluno": aluno,
        "exercicios": exercicios,
        "volume_total": float(total),
    }


def rejeitar_constante(valor):
    raise ErroHistorico(f"Número inválido no JSON: {valor}.")


def objeto_sem_duplicatas(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ErroHistorico(f"Campo duplicado no JSON: {chave}.")
        objeto[chave] = valor
    return objeto


def validar_numeros(objeto):
    if isinstance(objeto, float) and not math.isfinite(objeto):
        raise ErroHistorico("O histórico contém um número não finito.")
    if isinstance(objeto, dict):
        for valor in objeto.values():
            validar_numeros(valor)
    elif isinstance(objeto, list):
        for valor in objeto:
            validar_numeros(valor)


def ler_historico(caminho):
    """Aceita sessões antigas da aula, sem inventar datas ou corrigir seus dados."""
    try:
        with caminho.open("rb") as arquivo:
            original = arquivo.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return [], None
    if len(original) > MAX_BYTES:
        raise ErroHistorico("Histórico maior que 20 MiB. Migre para um banco de dados.")
    try:
        historico = json.loads(original.decode("utf-8-sig"),
                               parse_constant=rejeitar_constante,
                               object_pairs_hook=objeto_sem_duplicatas)
        if not isinstance(historico, list):
            raise ErroHistorico("O histórico deve ser uma lista de sessões.")
        ids = set()
        for sessao in historico:
            if (not isinstance(sessao, dict) or not isinstance(sessao.get("aluno"), str)
                    or not isinstance(sessao.get("exercicios"), list)
                    or not all(isinstance(e, dict) for e in sessao["exercicios"])):
                raise ErroHistorico("Sessão incompatível no histórico. O arquivo foi preservado.")
            if "id" in sessao:
                identificador = sessao["id"]
                if not isinstance(identificador, str) or not identificador or identificador in ids:
                    raise ErroHistorico("Identificação de sessão inválida ou duplicada.")
                ids.add(identificador)
        validar_numeros(historico)
    except (UnicodeError, ValueError, RecursionError) as erro:
        raise ErroHistorico(f"Não foi possível ler {caminho.name}: {erro}") from erro
    return historico, original


@contextmanager
def bloquear_historico(caminho):
    """Lock do sistema operacional: liberado também quando o processo termina."""
    lock = caminho.with_name(caminho.name + ".lock")
    with lock.open("a+b") as arquivo:
        arquivo.seek(0, os.SEEK_END)
        if arquivo.tell() == 0:
            arquivo.write(b"0")
            arquivo.flush()
        arquivo.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as erro:
            raise HistoricoOcupado("Histórico ocupado. Aguarde a outra gravação e tente novamente.") from erro
        try:
            yield
        finally:
            if os.name == "nt":
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
    # Não excluir o arquivo de lock: excluí-lo abre uma janela de concorrência.


def escrever_atomicamente(caminho, conteudo):
    """Grava e fecha um temporário antes de substituir o destino (inclusive no Windows)."""
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, prefix=caminho.name + ".",
                                         suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def salvar_sessao(sessao, caminho=ARQUIVO_HISTORICO):
    caminho = Path(caminho).resolve()
    with bloquear_historico(caminho):
        historico, original = ler_historico(caminho)
        # A mesma sessão pode ser reenviada após uma falha sem gerar duplicação.
        existentes = [s for s in historico if s.get("id") == sessao["id"]]
        if existentes:
            if existentes[0] != sessao:
                raise ErroHistorico("ID já usado por outra sessão. Nada foi substituído.")
            return
        historico.append(sessao)
        conteudo = (json.dumps(historico, ensure_ascii=False, indent=4,
                              allow_nan=False) + "\n").encode("utf-8")
        if len(conteudo) > MAX_BYTES:
            raise ErroHistorico("O novo histórico excederia 20 MiB. Nada foi gravado.")
        if original is not None:
            escrever_atomicamente(caminho.with_name(caminho.name + ".bak"), original)
        escrever_atomicamente(caminho, conteudo)


def main():
    print("TrackFit — registro local de treinos")
    print(f"Histórico: {ARQUIVO_HISTORICO}")
    print("Use Ctrl+C para cancelar. Carga 0 registra ausência de carga externa.")
    try:
        ler_historico(ARQUIVO_HISTORICO)  # Identifica corrupção antes de pedir o treino.
        sessao = coletar_sessao()
        print(f"\nResumo: {sessao['aluno']} — {len(sessao['exercicios'])} exercícios")
        print(f"Volume de carga externa da sessão: {sessao['volume_total']:g} kg")
        if not perguntar_sim_nao("Salvar esta sessão? (s/n): "):
            print("Sessão descartada. O histórico não foi alterado.")
            return 0
        while True:
            try:
                salvar_sessao(sessao)
                break
            except OSError as erro:
                print(f"Não foi possível confirmar o salvamento: {erro}")
                print("Os dados desta sessão continuam na memória enquanto o programa estiver aberto.")
                if not perguntar_sim_nao("Tentar salvar novamente? (s/n): "):
                    print("Salvamento não confirmado. Confira o histórico antes de refazer o registro.")
                    return 1
        print(f"Treino salvo! Sessão: {sessao['id']}")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nOperação interrompida. Se ocorreu durante a gravação, confira o histórico.")
        return 130
    except (ErroHistorico, OSError) as erro:
        print(f"\nNão foi possível concluir: {erro}")
        print("Não apague o histórico. Verifique o arquivo e a cópia .bak, se existir.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
