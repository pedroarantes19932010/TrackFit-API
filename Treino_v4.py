# 1. CONSTRUINDO A MÁQUINA
def calcular_volume(series, repeticoes, peso):
    volume_calc = series * repeticoes * peso
    return volume_calc

# 2. USANDO A MÁQUINA
volume_supino = calcular_volume(3, 10, 20)
volume_agachamento = calcular_volume(4, 8, 40)

print(f"Volume do Supino: {volume_supino} kg")
print(f"Volume do Agachamento: {volume_agachamento} kg")
