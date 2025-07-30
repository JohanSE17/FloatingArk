import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Simulated LSTM training (simplified for demonstration)
epochs = 50
train_loss = np.logspace(0, -2, num=epochs)  # Simulated loss decrease

plt.figure(figsize=(8, 6), dpi=300)
plt.plot(range(1, epochs + 1), train_loss, 'b-', label='Pérdida de Entrenamiento')
plt.title('Pérdida del Modelo LSTM Durante el Entrenamiento')
plt.xlabel('Época')
plt.ylabel('Pérdida (Log Scale)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig('img/lstm_loss.png', bbox_inches='tight')
plt.close()