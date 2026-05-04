def switch_pump(is_soil_dry: bool, is_raining: bool, is_tank_full: bool, is_manual: bool) -> bool:
    if (is_tank_full and is_manual) or (is_soil_dry and (not is_raining) and is_tank_full):
        return True
    return False

# Creating all 16 possible combinations of 4 inputs
combinations = [f"{i:04b}" for i in range(16)]

index = 0

for combination in combinations:
    is_soil_dry = bool(int(combination[0]))
    is_raining = bool(int(combination[1]))
    is_tank_full = bool(int(combination[2]))
    is_manual = bool(int(combination[3]))
    
    print(combination + f" ({index})")
    index += 1
    print("Pump is ON" if switch_pump(is_soil_dry, is_raining, is_tank_full, is_manual) else "Pump is OFF")
    print()
