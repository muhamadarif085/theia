# This file will contains the configuration dictionary for the model.
from tensorflow import keras
import os
from theia.model.custom_callback import CustomCallback

# This is the configuration dictionary for the model.
config = {
    "name": "mnist-handwriting", # This is the name of the model. If use_wandb is True, this will be the name of the Project in wandb.
    "id": "dense", # This is the id of the model. If use_wandb is True, this will be the name of the Run in wandb.
    "input_shape": [28, 28, 1], # This is the shape of the input data.
    "output_shape": 10, # Shape of the output data.
    "use_wandb": True, # Set to True to use wandb
    "optimizer": keras.optimizers.Adam(learning_rate=0.001), # Optimizer to use.
    "loss": keras.losses.CategoricalCrossentropy(), # Loss function to use.
    "metrics": [ # Metrics to use. Use the keras.metrics.Metric class.
        keras.metrics.CategoricalAccuracy()
    ],
    "batch_size": 32, # Batch size to use for training.
    "epochs": 2, # Number of epochs to train for.
    "callbacks": [ # Callbacks to use. Use the keras.callbacks.Callback class.
        CustomCallback()
    ],
    "checkpoint_state": "epoch", # "no_checkpoint" or "epoch". If "epoch", the model will be saved after each epoch. If "no_checkpoint", the model will not be saved.
    "checkpoint_dir": os.path.join(os.getcwd(), "history", "checkpoints"), # Directory to checkpoint the model to if checkpoint_state is "epoch".
    "save_dir": os.path.join(os.getcwd(), "history", "saved_models"), # Directory to save the model.
}

# Model definition goes here. Use the keras.layers.Layer class.
model_definition = keras.Sequential([
    # keras.layers.Conv2D(32, (3, 3), activation="relu", input_shape=config["input_shape"]),
    # keras.layers.MaxPooling2D(2, 2),
    # keras.layers.Conv2D(64, (3, 3), activation="relu"),
    # keras.layers.MaxPooling2D(2, 2),
    keras.layers.Flatten(),
    keras.layers.Dense(128, activation="relu"),
    keras.layers.Dense(config["output_shape"], activation="softmax")
])