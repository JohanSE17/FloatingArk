import time
from zapv2 import ZAPv2

# Configurar OWASP ZAP (asegúrate de que ZAP esté ejecutándose en localhost:8080)
zap = ZAPv2(proxies={'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})

# URL de la aplicación Flask
target = 'http://localhost:5000'

# Escanear
zap.urlopen(target)
zap.spider.scan(target)
time.sleep(2)

# Escaneo activo
zap.ascan.scan(target)
while int(zap.ascan.status()) < 100:
    time.sleep(5)

# Generar reporte
with open('zap_report.html', 'w') as f:
    f.write(zap.core.htmlreport())
logger.info("Escaneo de OWASP ZAP completado.")