import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Bidirectional, LSTM, Dense, Dropout, TimeDistributed
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

class BetaEllipticBiLSTMModel:
    def __init__(self, input_shape, num_elliptic_params=5):
        """
        Initialize the Beta-Elliptic BiLSTM model
        
        Args:
            input_shape: Tuple of (timesteps, features)
            num_elliptic_params: Number of parameters for elliptic components (default 5)
        """
        self.input_shape = input_shape
        self.num_elliptic_params = num_elliptic_params
        self.model = self.build_model()
        
    def build_model(self):
        """Build the BiLSTM model for beta-elliptic modeling"""
        # Input layer
        inputs = Input(shape=self.input_shape, name='input_layer')
        
        # First BiLSTM layer
        bilstm1 = Bidirectional(
            LSTM(128, return_sequences=True, dropout=0.2, recurrent_dropout=0.2),
            name='bilstm1'
        )(inputs)
        
        # Second BiLSTM layer
        bilstm2 = Bidirectional(
            LSTM(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2),
            name='bilstm2'
        )(bilstm1)
        
        # Beta distribution parameters (2 parameters per timestep)
        beta_output = TimeDistributed(
            Dense(2, activation='softplus'),
            name='beta_output'
        )(bilstm2)
        
        # Elliptic parameters (5 parameters per timestep)
        elliptic_output = TimeDistributed(
            Dense(self.num_elliptic_params, activation='linear'),
            name='elliptic_output'
        )(bilstm2)
        
        # Combine outputs
        model = Model(
            inputs=inputs,
            outputs=[beta_output, elliptic_output],
            name='beta_elliptic_bilstm'
        )
        
        # Custom loss function for beta and elliptic parameters
        def beta_loss(y_true, y_pred):
            return tf.keras.losses.mean_squared_error(y_true, y_pred)
            
        def elliptic_loss(y_true, y_pred):
            return tf.keras.losses.mean_absolute_error(y_true, y_pred)
        
        # Compile model
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss={
                'beta_output': beta_loss,
                'elliptic_output': elliptic_loss
            },
            loss_weights={
                'beta_output': 0.6,
                'elliptic_output': 0.4
            }
        )
        
        return model
    
    def train(self, X_train, y_beta_train, y_elliptic_train, 
              X_val=None, y_beta_val=None, y_elliptic_val=None,
              epochs=100, batch_size=32):
        """Train the model"""
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint('best_model.h5', save_best_only=True)
        ]
        
        validation_data = None
        if X_val is not None and y_beta_val is not None and y_elliptic_val is not None:
            validation_data = (X_val, {'beta_output': y_beta_val, 'elliptic_output': y_elliptic_val})
        
        history = self.model.fit(
            X_train,
            {
                'beta_output': y_beta_train,
                'elliptic_output': y_elliptic_train
            },
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks
        )
        
        return history
    
    def predict(self, X):
        """Make predictions"""
        return self.model.predict(X)
    
    def save(self, filepath):
        """Save the model"""
        self.model.save(filepath)
    
    def load(self, filepath):
        """Load a pre-trained model"""
        self.model = tf.keras.models.load_model(filepath)
        return self.model


# Example usage
if __name__ == "__main__":
    # Example data dimensions
    timesteps = 50
    features = 3  # Typically x, y, and pen state
    num_samples = 1000
    
    # Generate dummy data
    X = np.random.randn(num_samples, timesteps, features)
    y_beta = np.random.rand(num_samples, timesteps, 2)  # Alpha and beta parameters
    y_elliptic = np.random.randn(num_samples, timesteps, 5)  # Elliptic parameters
    
    # Split into train/validation
    split = int(0.8 * num_samples)
    X_train, X_val = X[:split], X[split:]
    y_beta_train, y_beta_val = y_beta[:split], y_beta[split:]
    y_elliptic_train, y_elliptic_val = y_elliptic[:split], y_elliptic[split:]
    
    # Initialize and train model
    model = BetaEllipticBiLSTMModel(input_shape=(timesteps, features))
    model.train(X_train, y_beta_train, y_elliptic_train, 
               X_val, y_beta_val, y_elliptic_val,
               epochs=50, batch_size=32)
    
    # Make predictions
    beta_pred, elliptic_pred = model.predict(X_val[:5])
    print("Beta predictions shape:", beta_pred.shape)
    print("Elliptic predictions shape:", elliptic_pred.shape)