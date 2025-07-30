def check_safety_mode(wind_speed, wave_height):
    if wind_speed > 50 or wave_height > 3:
        return "Activar modo de seguridad"
    else:
        return "Operación normal"

# Ejemplo de uso
wind_speed = 45  # km/h
wave_height = 2.5  # m
status = check_safety_mode(wind_speed, wave_height)
print(f"Estado: {status}")

wind_speed = 55
wave_height = 3.5
status = check_safety_mode(wind_speed, wave_height)
print(f"Estado: {status}")