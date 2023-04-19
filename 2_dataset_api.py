#!/usr/bin/env python
# coding: utf-8

# # TensorFlow Dataset API
# 
# **Learning Objectives**
# 1. Learn how to use tf.data to read data from memory
# 1. Learn how to use tf.data in a training loop
# 1. Learn how to use tf.data to read data from disk
# 1. Learn how to write production input pipelines with feature engineering (batching, shuffling, etc.)
# 
# 
# In this notebook, we will start by refactoring the linear regression we implemented in the previous lab so that it takes data from a`tf.data.Dataset`, and we will learn how to implement **stochastic gradient descent** with it. In this case, the original dataset will be synthetic and read by the `tf.data` API directly  from memory.
# 
# In a second part, we will learn how to load a dataset with the `tf.data` API when the dataset resides on disk.
# 
# Each learning objective will correspond to a __#TODO__  in this student lab notebook -- try to complete this notebook first and then review the [solution notebook](../solutions/2_dataset_api.ipynb).
# 

# In[52]:


import json
import math
import os
from pprint import pprint

import numpy as np
import tensorflow as tf
print(tf.version.VERSION)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


# ## Loading data from memory

# ### Creating the dataset

# Let's consider the synthetic dataset of the previous section:

# In[3]:


N_POINTS = 10
X = tf.constant(range(N_POINTS), dtype=tf.float32)
Y = 2 * X + 10


# We begin with implementing a function that takes as input
# 
# 
# - our $X$ and $Y$ vectors of synthetic data generated by the linear function $y= 2x + 10$
# - the number of passes over the dataset we want to train on (`epochs`)
# - the size of the batches the dataset (`batch_size`)
# 
# and returns a `tf.data.Dataset`: 

# **Remark:** Note that the last batch may not contain the exact number of elements you specified because the dataset was exhausted.
# 
# If you want batches with the exact same number of elements per batch, we will have to discard the last batch by
# setting:
# 
# ```python
# dataset = dataset.batch(batch_size, drop_remainder=True)
# ```
# 
# We will do that here.

# **Lab Task #1:** Complete the code below to 
# 1. instantiate a `tf.data` dataset using [tf.data.Dataset.from_tensor_slices](https://www.tensorflow.org/api_docs/python/tf/data/Dataset#from_tensor_slices).
# 2. Set up the dataset to 
#   * repeat `epochs` times,
#   * create a batch of size `batch_size`, ignoring extra elements when the batch does not divide the number of input elements evenly.

# In[4]:


# TODO 1
def create_dataset(X, Y, epochs, batch_size):
    dataset = tf.data.Dataset.from_tensor_slices((X,Y))  # TODO -- Your code here.
    dataset = dataset.repeat(epochs).batch(batch_size, drop_remainder=True) # TODO -- Your code here.
    return dataset


# Let's test our function by iterating twice over our dataset in batches of 3 datapoints:

# In[5]:


BATCH_SIZE = 3
EPOCH = 2

dataset = create_dataset(X, Y, epochs=EPOCH, batch_size=BATCH_SIZE)

for i, (x, y) in enumerate(dataset):
    print("x:", x.numpy(), "y:", y.numpy())
    assert len(x) == BATCH_SIZE
    assert len(y) == BATCH_SIZE


# ### Loss function and gradients

# The loss function and the function that computes the gradients are the same as before:

# In[6]:


def loss_mse(X, Y, w0, w1):
    Y_hat = w0 * X + w1
    errors = (Y_hat - Y)**2
    return tf.reduce_mean(errors)


def compute_gradients(X, Y, w0, w1):
    with tf.GradientTape() as tape:
        loss = loss_mse(X, Y, w0, w1)
    return tape.gradient(loss, [w0, w1])


# ### Training loop

# The main difference now is that now, in the traning loop, we will iterate directly on the `tf.data.Dataset` generated by our `create_dataset` function. 
# 
# We will configure the dataset so that it iterates 250 times over our synthetic dataset in batches of 2.

# **Lab Task #2:** Complete the code in the cell below to call your dataset above when training the model. Note that the `step, (X_batch, Y_batch)` iterates over the `dataset`. The inside of the `for` loop should be exactly as in the previous lab. 

# In[7]:


# TODO 2
EPOCHS = 250
BATCH_SIZE = 2
LEARNING_RATE = .02

MSG = "STEP {step} - loss: {loss}, w0: {w0}, w1: {w1}\n"

w0 = tf.Variable(0.0)
w1 = tf.Variable(0.0)

dataset = create_dataset(X, Y, epochs=EPOCHS, batch_size=BATCH_SIZE)   # TODO -- Your code here.

for step, (X_batch, Y_batch) in enumerate(dataset):    # TODO -- Your code here.

    dw0, dw1 = compute_gradients(X_batch, Y_batch, w0, w1) # TODO -- Your code here.
    # TODO -- Your code here.
    w0.assign_sub(dw0 * LEARNING_RATE)
    w1.assign_sub(dw1 * LEARNING_RATE)
    
    if step % 100 == 0:
        loss = loss_mse(X_batch, Y_batch, w0, w1) # TODO -- Your code here.
        print(MSG.format(step=step, loss=loss, w0=w0.numpy(), w1=w1.numpy()))
        
assert loss < 0.0001
assert abs(w0 - 2) < 0.001
assert abs(w1 - 10) < 0.001


# ## Loading data from disk

# ### Locating the CSV files
# 
# We will start with the **taxifare dataset** CSV files that we wrote out in a previous lab. 
# 
# The taxifare dataset files have been saved into `../toy_data`.
# 
# Check that it is the case in the cell below, and, if not, regenerate the taxifare
# 

# In[8]:


get_ipython().system('ls -l ../toy_data/taxi*.csv')


# ### Use tf.data to read the CSV files
# 
# The `tf.data` API can easily read csv files using the helper function tf.data.experimental.make_csv_dataset
# 
# If you have TFRecords (which is recommended), you may use tf.data.experimental.make_batched_features_dataset

# The first step is to define 
# 
# - the feature names into a list `CSV_COLUMNS`
# - their default values into a list `DEFAULTS`

# In[9]:


CSV_COLUMNS = [
    'fare_amount',
    'pickup_datetime',
    'pickup_longitude',
    'pickup_latitude',
    'dropoff_longitude',
    'dropoff_latitude',
    'passenger_count',
    'key'
]
LABEL_COLUMN = 'fare_amount'
DEFAULTS = [[0.0], ['na'], [0.0], [0.0], [0.0], [0.0], [0.0], ['na']]


# Let's now wrap the call to `make_csv_dataset` into its own function that will take only the file pattern (i.e. glob) where the dataset files are to be located:

# **Lab Task #3:** Complete the code in the `create_dataset(...)` function below to return a `tf.data` dataset made from the `make_csv_dataset`. Have a look at the [documentation here](https://www.tensorflow.org/api_docs/python/tf/data/experimental/make_csv_dataset). The `pattern` will be given as an argument of the function but you should set the `batch_size`, `column_names` and `column_defaults`.

# In[10]:


# TODO 3
def create_dataset(pattern):
    # TODO -- Your code here.
    dataset = tf.data.experimental.make_csv_dataset(pattern, 1, \
                                                    column_names=CSV_COLUMNS, \
                                                    column_defaults=DEFAULTS, \
                                                    label_name=LABEL_COLUMN, \
                                                    use_quote_delim=False, \
                                                    header=False)
    
    return dataset


tempds = create_dataset('../toy_data/taxi-train*')
print(tempds)


# Note that this is a prefetched dataset, where each element is an `OrderedDict` whose keys are the feature names and whose values are tensors of shape `(1,)` (i.e. vectors).
# 
# Let's iterate over the two first element of this dataset using `dataset.take(2)` and let's convert them ordinary Python dictionary with numpy array as values for more readability:

# In[22]:


#tempds.element_spec

#for features, label in tempds.take(2):
#    print("features------", features)
#    print()
#    print("label---------", label)
#    print()
#    print()
    
for data in tempds.take(2):
    pprint({k: v.numpy() for k, v in data.items()})
    print("\n")


# ### Transforming the features

# What we really need is a dictionary of features + a label. So, we have to do two things to the above dictionary:
# 
# 1. Remove the unwanted column "key"
# 1. Keep the label separate from the features
# 
# Let's first implement a function that takes as input a row (represented as an `OrderedDict` in our `tf.data.Dataset` as above) and then returns a tuple with two elements:
# 
# * The first element being the same `OrderedDict` with the label dropped
# * The second element being the label itself (`fare_amount`)
# 
# Note that we will need to also remove the `key` and `pickup_datetime` column, which we won't use.

# **Lab Task #4a:** Complete the code in the `features_and_labels(...)` function below. Your function should return a dictionary of features and a label. Keep in mind `row_data` is already a dictionary and you will need to remove the `pickup_datetime` and `key` from `row_data` as well.

# In[39]:


UNWANTED_COLS = ['pickup_datetime', 'key']

# TODO 4a
def features_and_labels(row_data):
    label = row_data[1]      # TODO -- Your code here.
    features = row_data[0]   # TODO -- Your code here.

    # TODO -- Your code here.
    for unwanted_col in UNWANTED_COLS:
        del features[unwanted_col]
    #features = features.items()
        
    return features, label


# Let's iterate over 2 examples from our `tempds` dataset and apply our `feature_and_labels`
# function to each of the examples to make sure it's working:

# In[40]:


for row_data in tempds.take(2):
    features, label = features_and_labels(row_data)
    pprint(features)
    print(label, "\n")
    assert UNWANTED_COLS[0] not in features.keys()
    assert UNWANTED_COLS[1] not in features.keys()
    assert label.shape == [1]


# ### Batching

# Let's now refactor our `create_dataset` function so that it takes an additional argument `batch_size` and batch the data correspondingly. We will also use the `features_and_labels` function we implemented for our dataset to produce tuples of features and labels.

# **Lab Task #4b:** Complete the code in the `create_dataset(...)` function below to return a `tf.data` dataset made from the `make_csv_dataset`. Now, the `pattern` and `batch_size` will be given as an arguments of the function but you should set the `column_names` and `column_defaults` as before. You will also apply a `.map(...)` method to create features and labels from each example. 

# In[43]:


# TODO 4b
def create_dataset(pattern, batch_size):
    dataset = tf.data.experimental.make_csv_dataset(
        # pattern, batch_size, CSV_COLUMNS, DEFAULTS)
        pattern, batch_size, \
        column_names=CSV_COLUMNS, \
        column_defaults=DEFAULTS, \
        label_name=LABEL_COLUMN, \
        use_quote_delim=False, \
        header=False)
    dataset = dataset.map(lambda x, y: features_and_labels((x,y))) # TODO -- Your code here.

    return dataset


# Let's test that our batches are of the right size:

# In[45]:


BATCH_SIZE = 2

tempds = create_dataset('../toy_data/taxi-train*', batch_size=2)

for X_batch, Y_batch in tempds.take(2):
    pprint({k: v.numpy() for k, v in X_batch.items()})
    print(Y_batch.numpy(), "\n")
    assert len(Y_batch) == BATCH_SIZE


# ### Shuffling
# 
# When training a deep learning model in batches over multiple workers, it is helpful if we shuffle the data. That way, different workers will be working on different parts of the input file at the same time, and so averaging gradients across workers will help. Also, during training, we will need to read the data indefinitely.

# Let's refactor our `create_dataset` function so that it shuffles the data, when the dataset is used for training.
# 
# We will introduce an additional argument `mode` to our function to allow the function body to distinguish the case
# when it needs to shuffle the data (`mode == 'train'`) from when it shouldn't (`mode == 'eval'`).
# 
# Also, before returning we will want to prefetch 1 data point ahead of time (`dataset.prefetch(1)`) to speed-up training:

# **Lab Task #4c:** The last step of our `tf.data` dataset will specify shuffling and repeating of our dataset pipeline. Complete the code below to add these three steps to the Dataset pipeline
# 1. follow the `.map(...)` operation which extracts features and labels with a call to `.cache()` the result.
# 2. during training, use `.shuffle(...)` and `.repeat()` to shuffle batches and repeat the dataset
# 3. use `.prefetch(...)` to take advantage of multi-threading and speedup training.

# In[57]:


# TODO 4c
def create_dataset(pattern, batch_size=1, mode='eval'):
    dataset = tf.data.experimental.make_csv_dataset(
        #pattern, batch_size, CSV_COLUMNS, DEFAULTS)
        pattern, batch_size, \
        column_names=CSV_COLUMNS, \
        column_defaults=DEFAULTS, \
        label_name=LABEL_COLUMN, \
        use_quote_delim=False, \
        header=False)
    
    dataset = dataset.map(lambda x, y: features_and_labels((x,y))) # TODO -- Your code here.

    if mode == 'train':
        dataset = dataset = dataset.shuffle(batch_size)  # TODO -- Your code here.

    # take advantage of multi-threading; 1=AUTOTUNE
    dataset = dataset.prefetch(1)                        # TODO -- Your code here.
    
    return dataset


# Let's check that our function works well in both modes:

# In[59]:


tempds = create_dataset('../toy_data/taxi-train*', 2, 'train')
print(list(tempds.take(1)))


# In[60]:


tempds = create_dataset('../toy_data/taxi-valid*', 2, 'eval')
print(list(tempds.take(1)))


# In the next notebook, we will build the model using this input pipeline.

# Copyright 2021 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
