from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import classification_report

# Regresión para energía de olas
X = subset_san_andres['VHM0'].values.flatten().reshape(-1, 1)
y = wave_energy_sa.values.flatten()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = LinearRegression()
model.fit(X_train, y_train)
score = model.score(X_test, y_test)
cv_scores = cross_val_score(model, X, y, cv=5)
logger.info(f'Precisión del modelo de regresión (R²): {score:.2f}')
logger.info(f'Validación cruzada (R²): {cv_scores.mean():.2f} ± {cv_scores.std():.2f}')

# Clasificación de condiciones de olas (optimización de KNN)
labels = np.where(X < 1, 'Calma', np.where(X < 3, 'Moderada', 'Extrema'))
X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, random_state=42)
param_grid = {'n_neighbors': [3, 5, 7, 9]}
knn = GridSearchCV(KNeighborsClassifier(), param_grid, cv=5)
knn.fit(X_train, y_train)
logger.info(f"Mejores parámetros KNN: {knn.best_params_}")
logger.info(f"Precisión del modelo KNN: {knn.score(X_test, y_test):.2f}")
logger.info("Reporte de clasificación KNN:\n" + classification_report(y_test, knn.predict(X_test)))

# Clasificación de presencia de ballenas
whale_pacific['presence'] = 1
no_whale = pd.DataFrame({'month': np.random.randint(1, 13, len(whale_pacific)), 'presence': 0})
whale_data_balanced = pd.concat([whale_pacific[['month', 'presence']], no_whale]).sample(frac=1).reset_index(drop=True)
X_whale = whale_data_balanced[['month']]
y_whale = whale_data_balanced['presence']
X_train, X_test, y_train, y_test = train_test_split(X_whale, y_whale, test_size=0.2, random_state=42)
nb = GaussianNB()
nb.fit(X_train, y_train)
accuracy = nb.score(X_test, y_test)
logger.info(f'Precisión del modelo Naive Bayes: {accuracy:.2f}')
logger.info("Reporte de clasificación Naive Bayes:\n" + classification_report(y_test, nb.predict(X_test)))