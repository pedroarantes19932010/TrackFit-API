aluno = input("Silvio Colombo")

# 1. Prancheta de Treinos
volume_do_treino = []

# 2. O loop 'for' repetirá este bloco 3 vezes para simular 3 exercícios

for exercicio in range(1, 4):
    print("\n--- Exercício" , exercicio, "---")
    peso_kg = int(input("Peso levantado (kg): "))
    series = int(input("Quantas séries? "))
    repeticoes = int(input("Quantas repetições? "))
    
    volume_exercicio = series * repeticoes * peso_kg
    
    # O comando .append() adiciona este novo volume à nossa lita
    volume_do_treino.append(volume_exercicio)

    print("Volume deste exercício:", volume_exercicio, "kg")

    # 3. Resultado Final
print("\n------------------------------------")
print("Resumo de Treino de: ", aluno)
print("Volume registrado na prancheta:", volume_do_treino)

    # A função sum() soma automaticamente todos os valores dentro desta lista
volume_total_treino = sum(volume_do_treino)
print("Volume total do treino:", volume_total_treino, "kg")
