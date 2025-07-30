import xarray as xr
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LinearRegression
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from datetime import datetime
import scipy.io as sio  # Para exportar a MATLAB
import logging  # Para manejo de logs
import sys
import warnings

# Configurar logging para monitorear el proceso
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ignorar advertencias innecesarias
warnings.filterwarnings('ignore')

# Verificar versiones de librerías clave
logger.info(f"Versión de xarray: {xr.__version__}")
logger.info(f"Versión de TensorFlow: {tf.__version__}")
logger.info(f"Versión de Pandas: {pd.__version__}")