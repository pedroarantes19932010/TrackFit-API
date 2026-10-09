print("--- Registro do Tracfit---")
aluno = input("Qual o nome do aluno?")
peso_kg = int(input("Qual foi o peso levantado (kg)?"))
series = int(input("Quantas séries?"))
repeticoes = int(input("Quantas repetições?"))
rpe = int(input("Qual a percepção de esforço (RPE)?"))

volume_total = series*repeticoes*peso_kg 

print("--------------------")
print("Aluno:", aluno)
print("Peso total levantado:", volume_total, "kg")

# Regra de Negócios: Inteligência de Deload

if rpe == 10:
    print("Alerta do Sistema: Esforço máximo atingido!")
else:
    print("Esforço dentro do limite seguro. Continue assim!")
