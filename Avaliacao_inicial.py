nome_do_aluno = input("Qual seu nome? ")
idade_do_aluno = int(input("Quantos anos você tem? "))
while True:
    sexo_do_aluno = input("Qual o seu sexo, masculino ou feminino? ")
    if sexo_do_aluno == "masculino" or sexo_do_aluno == "feminino":
        break
    else:
        print("Por favor, precisamos desta resposta: Qual foi seu sexo de nascimento?")
problemas_de_saude = input("Você tem algum problema de saúde que precisamos saber como; Hipertensão, diabetes ou cirurgias? ")
if problemas_de_saude == "sim":
    print("Precisamos saber quais as condições de saúde de maneira específica para te dar o melhor do nosso trabalho, então, poderia nos dizer quais problemas de saúde vc tem e nos enviar documentos em PDF ou Foto para abalisarmos melhor? ")
    print("Sua série será feita normalmente, porém em até 5 dias estaremos entrando em contato para darmos um melhor suporte a você na sua rotina de exercícios. Até lá, não pare!")
else:
    print("Ótimo! Vamos iniciar os treinos.")

local_de_treino = input("Qual será o local onde você fará seus exercícios; academia, ar livre, em casa? ")
if local_de_treino == "em casa":
    print("Preparar fixa para treinamento em casa")
elif local_de_treino == "academia":
    print("Preparar fixa para treinamento em academia")
elif local_de_treino == "ar livre":
    print("Preparar fixa para treinamento no ar livre")
else:
    print("Opção inválida, escolha entre; academia, ar livre ou em casa")
