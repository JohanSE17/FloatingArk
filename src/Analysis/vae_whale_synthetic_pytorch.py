# Definir el VAE en PyTorch
class VAE(nn.Module):
    def __init__(self, input_dim=3, hidden_dim=16, latent_dim=2):
        super(VAE, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim * 2)  # Para media y varianza
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        h = self.encoder(x)
        mu, logvar = h[:, :latent_dim], h[:, latent_dim:]
        z = self.reparameterize(mu, logvar)
        return self.decoder(z), mu, logvar

# Pérdida del VAE
def vae_loss(recon_x, x, mu, logvar):
    mse = nn.MSELoss()(recon_x, x)
    kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return mse + kld

# Entrenar VAE
whale_features = whale_pacific[['latitude', 'longitude', 'month']].values
scaler = StandardScaler()
whale_features_scaled = scaler.fit_transform(whale_features)
whale_features_tensor = torch.FloatTensor(whale_features_scaled)

vae = VAE()
optimizer = optim.Adam(vae.parameters(), lr=0.001)

num_epochs = 50
for epoch in range(num_epochs):
    optimizer.zero_grad()
    recon, mu, logvar = vae(whale_features_tensor)
    loss = vae_loss(recon, whale_features_tensor, mu, logvar)
    loss.backward()
    optimizer.step()

# Generar datos sintéticos
z_sample = torch.randn(100, latent_dim)
with torch.no_grad():
    synthetic_features = vae.decoder(z_sample).numpy()
synthetic_features = scaler.inverse_transform(synthetic_features)

# Visualizar
plt.figure(figsize=(10, 6))
plt.scatter(whale_features[:, 0], whale_features[:, 1], label='Datos reales', alpha=0.5)
plt.scatter(synthetic_features[:, 0], synthetic_features[:, 1], label='Datos sintéticos', alpha=0.5)
plt.title('Datos Reales vs Sintéticos - Avistamientos de Ballenas')
plt.xlabel('Latitud')
plt.ylabel('Longitud')
plt.legend()
plt.savefig('data/processed/vae_synthetic_whales.png')
logger.info("Datos sintéticos de avistamientos de ballenas generados con VAE.")