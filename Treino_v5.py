# 1. A nossa ferramenta (Função centralizada)
def calcular_volume(series, repeticoes, peso):
    volume_calc = series * repeticoes * peso
    return volume_calc

aluno = input("Nome do aluno: ")
treino_completo = []

# 2. O nosso fluxo de recolha de dados
for numero in range(1, 4):
    print(f"\n--- Exercício {numero} ---")
    
    nome_exercicio = input("Qual o exercício? ")
    peso_kg = int(input("Peso levantado (kg): "))
    series_feitas = int(input("Quantas séries? "))
    reps_feitas = int(input("Quantas repetições? "))

    # A TUA TAREFA AQUI:
    # Chama a função calcular_volume passando as três variáveis recolhidas acima nesta exata ordem: series_feitas, reps_feitas, peso_kg.
    # Guarda o resultado dentro da variável volume_final.
    volume_final = volume_final = calcular_volume(series_feitas, reps_feitas, peso_kg)

    # Criamos o JSON/Dicionário com o resultado limpo
    ficha_exercicio = {
        "exercicio": nome_exercicio,
        "volume_total": volume_final
    }
    treino_completo.append(ficha_exercicio)

print("\n--- Resumo Final (Estrutura JSON para a Base de Dados) ---")
print(treino_completo)