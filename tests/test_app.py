from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Configurar el navegador (asegúrate de tener ChromeDriver instalado)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.get("http://localhost:5000")

# Prueba: Verificar título de la página principal
assert "Floating Ark" in driver.title

# Prueba: Navegar al mapa interactivo
driver.find_element(By.LINK_TEXT, "Mapa").click()
time.sleep(2)
assert "Mapa Interactivo" in driver.page_source

driver.quit()
logger.info("Pruebas de Selenium completadas.")