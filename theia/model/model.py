# This module contains the model class and its methods for training.
from audioop import add
import os
from turtle import title
import tensorflow as tf
import numpy as np
from theia.model import config
from alive_progress import alive_bar
from wandb import wandb
from datetime import datetime
from uuid import uuid4

# TODO: Create prediction function that can be used to make predictions on new data.

class Model():
    def __init__(self, id = None):
        """
        Initialize the model class.
        """
        super(Model, self).__init__()

        self.config = config.config
        self.model = config.model_definition
        self.callbacks = tf.keras.callbacks.CallbackList(None, add_history=True)

        # Set the model id.
        if id is None:
            self.id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + str(uuid4())[:8]
        else:
            self.id = id
        
        # Set checkpoint.
        if self.config["checkpoint_state"] != "no_checkpoint":
            self.checkpoint = tf.train.Checkpoint(model=self.model, optimizer=self.config["optimizer"])
            self.checkpoint_manager = tf.train.CheckpointManager(self.checkpoint, self.config["checkpoint_dir"] + os.sep + self.config["name"] + os.sep + self.id, max_to_keep=5)
        
        # Warning if model checkpoint is enabled and wandb is enabled, the model should be given an id, so that if it run the checkpoint will be resumed from the same run-id on wandb.
        if self.config["checkpoint_state"] != "no_checkpoint" and self.config["use_wandb"] and id is None:
            print("\033[93mWARNING: Checkpoint is enabled but no id was given. This will cause the model to be saved on wandb with the same run-id as the checkpoint.\033[0m")

        # Check wandb.
        self.check_wandb_and_initilize()

        self.history = tf.keras.callbacks.History()
        self.callbacks.append(self.history)

        # Prompt user that model was created using green color.
        print("\033[32mModel created: " + self.config["name"] + "\033[0m")
    
    def check_wandb_and_initilize(self):
        """
        Check if wandb is enabled and initialize the wandb object.
        """

        # Check if wandb is enabled.
        if self.config["use_wandb"]:
            # Initialize the wandb object and set the project name. (Check if checkpoint_state is set to no_checkpoint and if not set the name into the id of the model.)
            if self.config["checkpoint_state"] != "no_checkpoint":
                self.wandb = wandb.init(project=self.config["name"], id=self.id, resume="allow")
                # Add wandb callback to the callbacks list.
                self.callbacks.append(wandb.keras.WandbCallback())
                print("\033[92mWandb initialized with project name: {} and id: {} USING checkpoint.\033[0m".format(self.config["name"], self.id))
            else:
                self.wandb = wandb.init(project=self.config["name"])
                # Add wandb callback to the callbacks list.
                self.callbacks.append(wandb.keras.WandbCallback())
                print("\033[92mWandb initialized with project name: {} and id: {} WITHOUT checkpoint.\033[0m".format(self.config["name"], self.id))

    def compile_metrics(self):
        """
        Compile the model with the given metrics.
        """
        # Compile the model.
        self.model.compile(
            optimizer=self.config["optimizer"],
            loss=self.config["loss"],
            metrics=self.config["metrics"]
        )

    def train(self, train_dataset, val_dataset):
        """
        This method is called when the model is trained.
        """

        # Check if use wandb or not
        use_wandb = self.config["use_wandb"]
        
        # Load all the callbacks.
        for callback in self.config["callbacks"]:
            self.callbacks.append(callback)
        
        # Append model to the callbacks list.
        self.callbacks.set_model(self.model)

        # Restore the model from the checkpoint.
        if self.config["checkpoint_state"] != "no_checkpoint":
            checkpoint_status = self.checkpoint_manager.restore_or_initialize()
            if checkpoint_status != None:
                print("\033[33mModel restored from checkpoint.\033[0m")

        # Iterate over metrics to calculate the loss and accuracy.
        metrics_dict = {"loss": 0}
        metrics_string = ""
        for metric in self.config["metrics"]:
            metric.reset_states()
            metrics_string += "loss: {:.4f} {}: {:.4f} ".format(0, metric.name, metric.result())
            metrics_dict[metric.name] = metric.result()

        # Get the number of batches in the dataset.
        train_batches = len(train_dataset)
        val_batches = len(val_dataset)
        num_batches = train_batches + val_batches

        self.callbacks.on_train_begin(metrics_dict)

        self.compile_metrics()

        # Print if the model is using wandb or not (print using yellow color).
        if use_wandb:
            print("\033[33mUsing Wandb, every logs will be redirected to wandb and will not be printed on the console.\033[0m")
        else:
            print("\033[33mNot using Wandb, every logs will be printed to the console.\033[0m")

        # Use the alive progress bar to show the progress of the training.
        with alive_bar(num_batches * self.config["epochs"], ctrl_c=False, manual=False, dual_line=True, spinner="dots_waves") as bar:

            # This is the training loop.
            for epoch in range(self.config["epochs"]):
                
                self.callbacks.on_epoch_begin(epoch, metrics_dict)

                # Setting the bar for each epoch.
                bar.title = "Epoch {}/{}".format(epoch + 1, self.config["epochs"])

                # Iterate over the training data.
                for batch, (images, labels) in enumerate(train_dataset):
                    
                    self.callbacks.on_batch_begin(batch, metrics_dict)
                    self.callbacks.on_train_batch_begin(batch, metrics_dict)

                    loss, predictions = self.train_step(images, labels)
                    
                    # Update the progress bar text.
                    bar.text = metrics_string

                    # Update metrics string with the new metrics.
                    if batch % 100 == 0:
                        metrics_string = "loss: {:.4f} ".format(loss.numpy())
                        metrics_dict["loss"] = loss.numpy()
                        for metric in self.config["metrics"]:
                            metrics_string += "{}: {:.4f} ".format(metric.name, metric.result())
                            metrics_dict[metric.name] = metric.result()

                    # Update the progress bar loading.
                    bar()

                    # If wandb is used, log the metrics.
                    # if use_wandb and batch % log_wandb_on == 0 and not log_on_epoch_end:
                    #     wandb.log(metrics_dict)

                    self.callbacks.on_train_batch_end(batch, metrics_dict)
                    self.callbacks.on_batch_end(batch, metrics_dict)
                
                # Iterate over metrics to calculate the loss and accuracy.
                val_metrics_string = ""
                for metric in self.config["metrics"]:
                    metric.reset_states()
                    val_metrics_string += "val_loss: {:.4f} val_{}: {:.4f} ".format(0, metric.name, metric.result())
                
                # Iterate over the validation data.
                for batch, (images, labels) in enumerate(val_dataset):
                    
                    self.callbacks.on_batch_begin(batch, metrics_dict)
                    self.callbacks.on_test_batch_begin(batch, metrics_dict)

                    # Compute the loss and predictions.
                    loss, predictions = self.val_train_step(images, labels)

                    # Update the progress bar text.
                    bar.text = val_metrics_string

                    # Update the metrics string with the new metrics.
                    if batch % 100 == 0:
                        val_metrics_string  = "val_loss: {:.4f} ".format(loss.numpy())
                        metrics_dict["val_loss"] = loss.numpy()
                        for metric in self.config["metrics"]:
                            val_metrics_string += "val_{}: {:.4f} ".format(metric.name, metric.result())
                            metrics_dict["val_{}".format(metric.name)] = metric.result()

                    # Update the progress bar.
                    # bar(counter / num_batches)
                    # counter += 1
                    bar()

                    # If wandb is used, log the metrics.
                    # if use_wandb and batch % log_wandb_on == 0 and not log_on_epoch_end:
                    #     wandb.log(metrics_dict)

                    self.callbacks.on_test_batch_end(batch, metrics_dict)
                    self.callbacks.on_batch_end(batch, metrics_dict)

                # Print the epoch and training metrics and validation metrics.
                if not use_wandb:
                    print("epoch {}: {} {}\n".format(epoch + 1, metrics_string, val_metrics_string))

                # If log_on_epoch_end is True, log the metrics.
                # if use_wandb and log_on_epoch_end:
                #     wandb.log(metrics_dict)

                # Save the model if the checkpoint_on_epoch_end is True.
                if self.config["checkpoint_state"] == "epoch":
                    self.checkpoint_manager.save()

                self.callbacks.on_epoch_end(epoch, metrics_dict)
        
        self.callbacks.on_train_end(metrics_dict)
    
    def train_step(self, images, labels):
        """
        This method is used to train the model in a single step.
        """
        # Open Gradient Tape.
        with tf.GradientTape() as tape:
            # Compute the loss.
            predictions = self.model(images, training=True)
            loss = self.config["loss"](labels, predictions)

        # Iterate over the metrics and update them.
        for metric in self.config["metrics"]:
            metric.update_state(labels, predictions)
        
        # Compute the gradients.
        gradients = tape.gradient(loss, self.model.trainable_weights)
        
        # Apply the gradients.
        self.config["optimizer"].apply_gradients(zip(gradients, self.model.trainable_weights))

        return loss, predictions
    
    def val_train_step(self, images, labels):
        """
        This method is used to validate the model in a single step.
        """
        # Compute the loss.
        predictions = self.model(images, training=False)
        loss = self.config["loss"](labels, predictions)

        # Calculate the metrics.
        for metric in self.config["metrics"]:
            metric.update_state(labels, predictions)

        return loss, predictions

    def save(self, dir_path):
        """
        Save the model to the given path.
        """

        # Create the model directory.
        model_path = os.path.join(dir_path, "saved_model", self.config["name"], self.id)

        # Create directory for the model.
        if not os.path.exists(model_path):
            os.makedirs(model_path)

        # Save the model.
        self.model.save_weights(model_path + os.sep + "model.h5")

        # Log to user that the model was saved using green color.
        print("\033[92mModel saved to {}\033[0m".format(model_path))

    def add_checkpoint_callback(self):
        """
        Create a checkpoint callback to save the model every epoch.
        """

        # Create the directory for the model.
        model_path = os.path.join(self.config["checkpoint_dir"], "checkpoints", self.id)

        # Create directory for the model.
        if not os.path.exists(model_path):
            os.makedirs(model_path)

        # Create the checkpoint callback.
        checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(model_path, "{epoch:02d}-{val_loss:.2f}.hdf5"),
            save_weights_only=True,
            save_best_only=True,
            monitor="val_loss",
            verbose=0,
            period=1
        )

        # Add the callback to the callbacks list.
        self.callbacks.append(checkpoint_callback)

        # Log to user that the checkpoint callback was added using yellow color.
        print("\033[33mCheckpoint callback added. The model will be saved every epoch in {}.\033[0m".format(self.config["checkpoint_dir"]))
    
    def predict(self, images, batch_size=None, verbose=False):
        """
        This method is used to predict the labels for the given images.
        """
        # If batch_size is None, use the default batch size.
        if batch_size is None:
            batch_size = self.config["batch_size"]

        # Create the dataset.
        dataset = tf.data.Dataset.from_tensor_slices(images)
        dataset = dataset.batch(batch_size)

        # Iterate over the dataset.
        predictions = []
        for batch, (images) in enumerate(dataset):
            # Compute the predictions.
            predictions.append(self.model(images, training=False))

        # Return the predictions.
        return np.concatenate(predictions, axis=0)