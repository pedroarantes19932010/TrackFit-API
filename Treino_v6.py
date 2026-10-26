import json # 1. Dados mantidos

def calcular_volume(series, repeticoes, peso):
    volume_calc = series * repeticoes * peso
    return volume_calc

aluno = input("Nome do aluno: ")
treino_completo = []

for numero in range(1, 4):
    print(f"\n--- Exercício {numero} ---")
    nome_exercicio = input("Qual o exercício? ")
    peso_kg = int(input("Peso levantado (kg): "))
    series_feitas = int(input("Quantas séries? "))
    reps_feitas = int(input("Quantas repetições? "))

    volume_final = calcular_volume(series_feitas, reps_feitas, peso_kg)

    ficha_exercicio = {
        "exercicio": nome_exercicio,
        "volume_total": volume_final
    }
    treino_completo.append(ficha_exercicio)

# 2. Permanencia de Dados
with open("banco_de_dados.json", "w") as ficheiro:
    
    json.dump(treino_completo, ficheiro, indent=4)

print(f"\nSucesso! O treino do(a) {aluno} foi guardado no banco de dados.")