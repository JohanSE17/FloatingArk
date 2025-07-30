import torch
import torch.nn as nn
import torch.optim as optim

# Definir el modelo LSTM en PyTorch
class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=50, num_layers=2):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, dropout=0.2, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

# Entrenar LSTM para cada región
for region, subset in wave_energy_dict.items():
    wave_height_1d = subset['VHM0'].mean(dim=['latitude', 'longitude']).values
    X = np.array([wave_height_1d[i:i+10] for i in range(len(wave_height_1d)-10)])
    y = wave_height_1d[10:]
    X = X.reshape(X.shape[0], X.shape[1], 1)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Convertir a tensores de PyTorch
    X_train = torch.FloatTensor(X_train)
    y_train = torch.FloatTensor(y_train).view(-1, 1)
    X_test = torch.FloatTensor(X_test)
    y_test = torch.FloatTensor(y_test).view(-1, 1)

    # Crear modelo
    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Entrenar modelo
    num_epochs = 50
    train_losses, val_losses = [], []
    for epoch in range(num_epochs):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        train_losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            val_outputs = model(X_test)
            val_loss = criterion(val_outputs, y_test)
            val_losses.append(val_loss.item())

    # Visualizar resultados
    plt.figure(figsize=(10, 6))
    plt.plot(train_losses, label='Pérdida de entrenamiento')
    plt.plot(val_losses, label='Pérdida de validación')
    plt.title(f'Pérdida del Modelo LSTM - {region}')
    plt.xlabel('Época')
    plt.ylabel('Pérdida (MSE)')
    plt.legend()
    plt.savefig(f'data/processed/lstm_loss_{region.replace(" ", "_").lower()}.png')

    # Predicciones
    model.eval()
    with torch.no_grad():
        y_pred = model(X_test).numpy()
    plt.figure(figsize=(10, 6))
    plt.plot(y_test.numpy()[:100], label='Valores reales')
    plt.plot(y_pred[:100], label='Predicciones')
    plt.title(f'Predicciones de Altura de Olas - {region}')
    plt.xlabel('Muestra')
    plt.ylabel('Altura (m)')
    plt.legend()
    plt.savefig(f'data/processed/lstm_predictions_{region.replace(" ", "_").lower()}.png')

    mae = mean_absolute_error(y_test.numpy(), y_pred)
    rmse = mean_squared_error(y_test.numpy(), y_pred, squared=False)
    logger.info(f"MAE del modelo LSTM ({region}): {mae:.2f}")
    logger.info(f"RMSE del modelo LSTM ({region}): {rmse:.2f}")