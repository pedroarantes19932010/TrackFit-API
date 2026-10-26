while True:
    pergunta_inicial = input("Você já fez exercícios antes como musculação, funcional ou calistenia? ").strip().lower()
    
    if pergunta_inicial == "sim" or pergunta_inicial == "não":
        break
    else:
        print("Por favor, responda apenas 'sim' ou 'não'.")

while True:
    resposta_bruta = input("Quanto tempo você pratica ou já praticou exercícios físicos (em meses)? ")
    apenas_numeros = "".join(caractere for caractere in resposta_bruta if caractere.isdigit())
    
    if apenas_numeros != "": 
        tempo_de_experiencia = int(apenas_numeros)
        break
    else:
        print("Por favor, inclua o número de meses na sua resposta (ex: '3 meses').")

if tempo_de_experiencia <= 1:
    print("Aplicar protocolo padrão. Reduzir a carga drasticamente e focar na percepção de esforço.")
else:
    print("Aplicar protocolo padrão com foco em cargas altas e métodos de exaustão.")