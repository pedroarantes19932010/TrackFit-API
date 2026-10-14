aluno = input("Nome do aluno: ")
treino_completo = [] #lista principal vazia

for numero in range(1, 4):
    print(f"\n--- Exercício {numero} ---")

    nome_exercicio = input("Qual o exercício? ")
    peso_kg = int(input("Peso levantado (kg): "))
    series = int(input("Quaantas séries? "))
    repeticoes = int(input("Qauntas repetições? "))

    volume_calc =  series * repeticoes * peso_kg

    # Criamos o Dicionário (ficha estruturada)
    ficha_exercicio = {
        "exercício": nome_exercicio,
        "Volume_total": volume_calc
    }
    
    # Guardamos o dicionário inteiro dentro da nossa lista
    treino_completo.append(ficha_exercicio)

print("\n------------------------------------")
print(f"Resumo do Treino de: {aluno}")
print("Dados estruturados (formato JSON/API):")
print(treino_completo)
