import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import Treino_v6 as app


class RegistroTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'historico_treinos.json'

    def sessao(self, identificador='s1'):
        return {'id': identificador, 'aluno': 'Pedro', 'exercicios': []}

    def test_peso_decimal_e_zero(self):
        for texto, esperado in [('12,5', '12.5'), ('12.5', '12.5'), ('0', '0'), (' 2.125 ', '2.125')]:
            self.assertEqual(str(app.converter_peso(texto)), esperado)

    def test_pesos_invalidos(self):
        for texto in ['', '-1', 'nan', 'NaN', 'inf', 'Infinity', '1e999', '12 kg', '1,000.5', '2.1234', '10001']:
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                app.converter_peso(texto)

    def test_inteiros_invalidos(self):
        for texto in ['', '0', '-2', '2,5', '2.0', 'dez', '1 mês', '101', '9' * 5000]:
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                app.converter_inteiro(texto, 1, 100)

    def test_textos(self):
        self.assertEqual(app.validar_texto('  João Silva  '), 'João Silva')
        for texto in ['', '   ', 'a' * 121, 'nome\x00']:
            with self.assertRaises(ValueError):
                app.validar_texto(texto)

    def test_volume_e_validacao(self):
        self.assertEqual(app.calcular_volume(3, 12, 40), 1440)
        self.assertEqual(str(app.calcular_volume(3, 10, '12.5')), '375.0')
        for args in [(True, 10, 20), (0, 10, 20), (3, -1, 20), (3, 10, -1)]:
            with self.assertRaises(ValueError):
                app.calcular_volume(*args)

    def test_repeticao_de_nome_vazio_e_numeros_invalidos(self):
        respostas = ['', '  ', 'Supino', 'abc', '2', 's', 'nan', '12,5', '0', '10']
        with patch('builtins.input', side_effect=respostas), contextlib.redirect_stdout(io.StringIO()):
            exercicio = app.coletar_exercicio(1)
        self.assertEqual(exercicio['volume_total'], 250)
        self.assertEqual(len(exercicio['series_detalhes']), 2)
        self.assertEqual(exercicio['peso_kg'], 12.5)

    def test_series_diferentes(self):
        with patch('builtins.input', side_effect=['Remada', '2', 'n', '10', '12', '12,5', '8']), contextlib.redirect_stdout(io.StringIO()):
            exercicio = app.coletar_exercicio(1)
        self.assertEqual(exercicio['volume_total'], 220)
        self.assertNotIn('peso_kg', exercicio)
        self.assertEqual(exercicio['series_detalhes'][1]['repeticoes'], 8)

    def test_sessao_com_data_id_total(self):
        with patch('builtins.input', side_effect=['José', '1', 'Agachamento', '1', '0', '10']), contextlib.redirect_stdout(io.StringIO()):
            sessao = app.coletar_sessao()
        self.assertEqual(sessao['volume_total'], 0)
        self.assertEqual(sessao['versao_formato'], 2)
        self.assertIsNotNone(app.datetime.fromisoformat(sessao['registrado_em']).tzinfo)
        self.assertEqual(len(sessao['id']), 36)

    def test_duas_sessoes_backup_e_idempotencia(self):
        app.salvar_sessao(self.sessao(), self.path)
        primeiro = self.path.read_bytes()
        app.salvar_sessao(self.sessao('s2'), self.path)
        app.salvar_sessao(self.sessao('s2'), self.path)
        self.assertEqual(len(app.ler_historico(self.path)[0]), 2)
        self.assertEqual(self.path.with_name(self.path.name + '.bak').read_bytes(), primeiro)

    def test_id_igual_com_dados_diferentes_nao_sobrescreve(self):
        app.salvar_sessao(self.sessao(), self.path)
        original = self.path.read_bytes()
        outra = self.sessao()
        outra['aluno'] = 'Outro'
        with self.assertRaises(app.ErroHistorico):
            app.salvar_sessao(outra, self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_preserva_sessao_antiga_sem_inventar_dados(self):
        antiga = [{'aluno': 'pedro', 'exercicios': [{'exercicio': '', 'volume_total': 15}]}]
        self.path.write_text(json.dumps(antiga), encoding='utf-8')
        app.salvar_sessao(self.sessao(), self.path)
        self.assertEqual(app.ler_historico(self.path)[0][0], antiga[0])

    def test_corrupcao_nunca_apaga_original(self):
        invalidos = [b'', b'{', b'{}', b'[null]', b'[{"exercicio":"supino"}]', b'\xff',
                     b'[{"aluno":"a","exercicios":[],"x":NaN}]',
                     b'[{"aluno":"a","exercicios":[],"x":1e999}]',
                     b'[{"aluno":"a","aluno":"b","exercicios":[]}]',
                     b'[{"aluno":"a","exercicios":[],"id":[]}]']
        for original in invalidos:
            self.path.write_bytes(original)
            with self.subTest(original=original), self.assertRaises(app.ErroHistorico):
                app.salvar_sessao(self.sessao(), self.path)
            self.assertEqual(self.path.read_bytes(), original)

    def test_utf8_bom(self):
        self.path.write_text('[{"aluno":"José","exercicios":[]}]', encoding='utf-8-sig')
        self.assertEqual(app.ler_historico(self.path)[0][0]['aluno'], 'José')

    def test_falha_substituicao_preserva_original_e_limpa_temporario(self):
        app.salvar_sessao(self.sessao(), self.path)
        original = self.path.read_bytes()
        real_replace = os.replace
        def falhar_no_historico(origem, destino):
            if Path(destino) == self.path:
                raise PermissionError('Arquivo bloqueado')
            real_replace(origem, destino)
        with patch.object(app.os, 'replace', side_effect=falhar_no_historico), self.assertRaises(PermissionError):
            app.salvar_sessao(self.sessao('s2'), self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        app.salvar_sessao(self.sessao('s2'), self.path)  # lock liberado após falha
        self.assertEqual(len(app.ler_historico(self.path)[0]), 2)

    def test_falha_disco_preserva_original(self):
        app.salvar_sessao(self.sessao(), self.path)
        original = self.path.read_bytes()
        with patch.object(app.os, 'fsync', side_effect=OSError('Sem espaço')), self.assertRaises(OSError):
            app.salvar_sessao(self.sessao('s2'), self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_arquivo_grande_nao_sobrescreve(self):
        self.path.write_bytes(b' ' * 101)
        with patch.object(app, 'MAX_BYTES', 100), self.assertRaises(app.ErroHistorico):
            app.salvar_sessao(self.sessao(), self.path)
        self.assertEqual(self.path.stat().st_size, 101)

    def test_outro_processo_respeita_lock(self):
        codigo = ('import sys; from pathlib import Path; import Treino_v6 as a; '
                  'a.salvar_sessao({"id":"outro","aluno":"Teste","exercicios":[]}, Path(sys.argv[1]))')
        with app.bloquear_historico(self.path):
            processo = subprocess.run([sys.executable, '-c', codigo, str(self.path)],
                                      cwd=Path(app.__file__).parent, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(processo.returncode, 0)
        self.assertIn('HistoricoOcupado', processo.stderr)
        self.assertFalse(self.path.exists())
        app.salvar_sessao(self.sessao(), self.path)

    def test_lock_liberado_apos_morte_do_processo(self):
        codigo = ('import sys; from pathlib import Path; import Treino_v6 as a; '
                  'ctx=a.bloquear_historico(Path(sys.argv[1])); ctx.__enter__(); '
                  'print("pronto", flush=True); sys.stdin.read()')
        processo = subprocess.Popen([sys.executable, '-c', codigo, str(self.path)],
                                   cwd=Path(app.__file__).parent, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(processo.stdout.readline().strip(), 'pronto')
            processo.kill()
            processo.communicate(timeout=10)
            app.salvar_sessao(self.sessao(), self.path)
        finally:
            if processo.poll() is None:
                processo.kill()
                processo.communicate()

    def test_cancelamento_nao_cria_historico(self):
        for erro in [KeyboardInterrupt, EOFError]:
            with patch.object(app, 'ARQUIVO_HISTORICO', self.path), patch('builtins.input', side_effect=erro), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(app.main(), 130)
            self.assertFalse(self.path.exists())

    def test_recusa_confirmacao_nao_salva(self):
        with patch.object(app, 'ARQUIVO_HISTORICO', self.path), patch.object(app, 'coletar_sessao', return_value={**self.sessao(), 'volume_total': 0}), patch('builtins.input', return_value='n'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.main(), 0)
        self.assertFalse(self.path.exists())

    def test_caminho_independe_da_pasta_terminal(self):
        codigo = 'import Treino_v6 as a; print(a.ARQUIVO_HISTORICO)'
        env = dict(os.environ, PYTHONPATH=str(Path(app.__file__).parent))
        processo = subprocess.run([sys.executable, '-c', codigo], cwd=self.temp.name,
                                  env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(processo.returncode, 0, processo.stderr)
        self.assertEqual(Path(processo.stdout.strip()), app.ARQUIVO_HISTORICO)
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_fluxo_completo_em_copia_isolada(self):
        destino = self.path.parent / 'Treino_v6.py'
        destino.write_bytes(Path(app.__file__).read_bytes())
        entrada = 'Pedro\n1\n\nSupino\n1\n12,5\n10\ns\n'
        for _ in range(2):
            processo = subprocess.run([sys.executable, str(destino)], cwd=Path(app.__file__).parent,
                                      input=entrada, capture_output=True, text=True, timeout=10)
            self.assertEqual(processo.returncode, 0, processo.stderr)
            self.assertIn('Treino salvo!', processo.stdout)
        historico, _ = app.ler_historico(self.path)
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0]['volume_total'], 125)
        self.assertNotEqual(historico[0]['id'], historico[1]['id'])


if __name__ == '__main__':
    unittest.main()
