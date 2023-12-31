# -*- coding: utf-8 -*-
"""2Dkspace.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jn9l0XWK0cVUv162y6iJMJhbiZJy23t6
"""

# Allow access to google drive files
from google.colab import drive
drive.mount('/content/gdrive')

import h5py
import numpy as np
import matplotlib.pyplot as plt
import torch
import torchvision
from torchvision import transforms
from torch.utils.data import TensorDataset, DataLoader



# Loading data from hdf5 file and creating numpy arrays
hdf5_path = '/content/gdrive/My Drive/Colab Notebooks/dataset.hdf5'
f = h5py.File(hdf5_path,"r")
print(list(f.keys()))
x = f['trnOrg'][()] # set of ground-truth
P = f['trnMask'][()] # sampling operator
F = [np.fft.fft2(img) for img in x] # list of Fourier transforms of set of ground-truth
'''
# Normalization of images in k-space
for i in range(X.shape[0]):
  X[i] /= np.amax(np.abs(X[i]))
'''
X = np.array(F)
e = np.zeros(x.shape) # noise vector (0 for now)
y = P*X+e # noisy measurement


# Creating 4D arrays of shape (N, in_chans, H, W) for ground-truth and noisy measurement
x_img = np.zeros((X.shape[0],2,X.shape[1],X.shape[2]))
x_img[:,0,:,:] = X.real
x_img[:,1,:,:] = X.imag

y_img = np.zeros((y.shape[0],2,y.shape[1],y.shape[2]))
y_img[:,0,:,:] = y.real
y_img[:,1,:,:] = y.imag

# Split the data into training, validation, and testing sets (80%-10%-10%)
from sklearn.model_selection import train_test_split

train_X,rem_X,train_ground,rem_ground = train_test_split(y_img,x_img,train_size = 0.8)
valid_X,test_X,valid_ground,test_ground= train_test_split(rem_X,rem_ground,test_size = 0.5)


# Convert to tensors
train_X = torch.Tensor(train_X)
train_ground = torch.Tensor(train_ground)
valid_X = torch.Tensor(valid_X)
valid_ground = torch.Tensor(valid_ground)
test_X = torch.Tensor(test_X)
test_ground = torch.Tensor(test_ground)

# Creating datasets of tensors
trainset = TensorDataset(train_X,train_ground)
valset = TensorDataset(valid_X,valid_ground)
testset = TensorDataset(test_X,test_ground)

# Using dataloader class
train_loader = DataLoader(trainset,batch_size=16,shuffle=True)
val_loader = DataLoader(trainset,batch_size=16,shuffle=True)
test_loader = DataLoader(testset,batch_size=16,shuffle=True)

# Unet model
# from https://github.com/facebookresearch/fastMRI/blob/main/fastmri/models/unet.py

from torch.nn import Module, Conv2d, Linear, MaxPool2d,  ReLU, Dropout
from torch import flatten

"""
Copyright (c) Facebook, Inc. and its affiliates.
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import torch
from torch import nn
from torch.nn import functional as F


class Unet(nn.Module):
    """
    PyTorch implementation of a U-Net model.
    O. Ronneberger, P. Fischer, and Thomas Brox. U-net: Convolutional networks
    for biomedical image segmentation. In International Conference on Medical
    image computing and computer-assisted intervention, pages 234–241.
    Springer, 2015.
    """

    def __init__(
        self,
        in_chans: int,
        out_chans: int,
        chans: int = 32,
        num_pool_layers: int = 4,
        drop_prob: float = 0.0,
    ):
        """
        Args:
            in_chans: Number of channels in the input to the U-Net model.
            out_chans: Number of channels in the output to the U-Net model.
            chans: Number of output channels of the first convolution layer.
            num_pool_layers: Number of down-sampling and up-sampling layers.
            drop_prob: Dropout probability.
        """
        super().__init__()

        self.in_chans = in_chans
        self.out_chans = out_chans
        self.chans = chans
        self.num_pool_layers = num_pool_layers
        self.drop_prob = drop_prob

        self.down_sample_layers = nn.ModuleList([ConvBlock(in_chans, chans, drop_prob)])
        ch = chans
        for _ in range(num_pool_layers - 1):
            self.down_sample_layers.append(ConvBlock(ch, ch * 2, drop_prob))
            ch *= 2
        self.conv = ConvBlock(ch, ch * 2, drop_prob)

        self.up_conv = nn.ModuleList()
        self.up_transpose_conv = nn.ModuleList()
        for _ in range(num_pool_layers - 1):
            self.up_transpose_conv.append(TransposeConvBlock(ch * 2, ch))
            self.up_conv.append(ConvBlock(ch * 2, ch, drop_prob))
            ch //= 2

        self.up_transpose_conv.append(TransposeConvBlock(ch * 2, ch))
        self.up_conv.append(
            nn.Sequential(
                ConvBlock(ch * 2, ch, drop_prob),
                nn.Conv2d(ch, self.out_chans, kernel_size=1, stride=1),
            )
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: Input 4D tensor of shape `(N, in_chans, H, W)`.
        Returns:
            Output tensor of shape `(N, out_chans, H, W)`.
        """
        stack = []
        output = image

        # apply down-sampling layers
        for layer in self.down_sample_layers:
            output = layer(output)
            stack.append(output)
            output = nn.MaxPool2d(kernel_size=2, stride=2)(output)

        output = self.conv(output)

        # apply up-sampling layers
        for transpose_conv, conv in zip(self.up_transpose_conv, self.up_conv):
            downsample_layer = stack.pop()
            output = transpose_conv(output)

            # reflect pad on the right/botton if needed to handle odd input dimensions
            padding = [0, 0, 0, 0]
            if output.shape[-1] != downsample_layer.shape[-1]:
                padding[1] = 1  # padding right
            if output.shape[-2] != downsample_layer.shape[-2]:
                padding[3] = 1  # padding bottom
            if torch.sum(torch.tensor(padding)) != 0:
                output = F.pad(output, padding, "reflect")

            output = torch.cat([output, downsample_layer], dim=1)
            output = conv(output)

        return output


class ConvBlock(nn.Module):
    """
    A Convolutional Block that consists of two convolution layers each followed by
    instance normalization, LeakyReLU activation and dropout.
    """

    def __init__(self, in_chans: int, out_chans: int, drop_prob: float):
        """
        Args:
            in_chans: Number of channels in the input.
            out_chans: Number of channels in the output.
            drop_prob: Dropout probability.
        """
        super().__init__()

        self.in_chans = in_chans
        self.out_chans = out_chans
        self.drop_prob = drop_prob

        self.layers = nn.Sequential(
            nn.Conv2d(in_chans, out_chans, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm2d(out_chans),
            nn.LeakyReLU(negative_slope=0.2, inplace=True),
            nn.Dropout2d(drop_prob),
            nn.Conv2d(out_chans, out_chans, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm2d(out_chans),
            nn.LeakyReLU(negative_slope=0.2, inplace=True),
            nn.Dropout2d(drop_prob),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: Input 4D tensor of shape `(N, in_chans, H, W)`.
        Returns:
            Output tensor of shape `(N, out_chans, H, W)`.
        """
        return self.layers(image)


class TransposeConvBlock(nn.Module):
    """
    A Transpose Convolutional Block that consists of one convolution transpose
    layers followed by instance normalization and LeakyReLU activation.
    """

    def __init__(self, in_chans: int, out_chans: int):
        """
        Args:
            in_chans: Number of channels in the input.
            out_chans: Number of channels in the output.
        """
        super().__init__()

        self.in_chans = in_chans
        self.out_chans = out_chans

        self.layers = nn.Sequential(
            nn.ConvTranspose2d(
                in_chans, out_chans, kernel_size=2, stride=2, bias=False
            ),
            nn.InstanceNorm2d(out_chans),
            nn.LeakyReLU(negative_slope=0.2, inplace=True),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: Input 4D tensor of shape `(N, in_chans, H, W)`.
        Returns:
            Output tensor of shape `(N, out_chans, H*2, W*2)`.
        """
        return self.layers(image)
print('done')

# Set model to run on GPU if available, otherwise use CPU
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("The model will be running on", device, "device")
# Setting up unet model, loss function, and optimizer
model = Unet(in_chans=2,
        out_chans=2,
        chans = 32,
        num_pool_layers = 4,
        drop_prob  = 0.0)
model.to(device) # load model onto GPU
loss_fn = torch.nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# print model information
#print(model)

'''
Function for training the model
Based on content from:
https://pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html
https://learn.microsoft.com/en-us/windows/ai/windows-ml/tutorials/pytorch-train-model
parameters: dataloader - dataloader class, model - model for training,
            loss_fn - loss function for training, optimizer - optimizer for training
output: print statements showing the batch number and the loss
'''
def train(dataloader, model, loss_fn, optimizer):
    size = len(dataloader.dataset)
    model.train()
    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device) # load X and y onto GPU
        # Compute prediction error
        pred = model(X)
        loss = loss_fn(pred, y)

        # Backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch % 5 == 0:
            loss, current = loss.item(), batch * len(X)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")
print('done')

'''
Function for testing the model
parameters: dataloader - dataloader class, model - model for training,
            loss_fn - loss function for training
output: print statement showing the average loss
'''
def test(dataloader, model, loss_fn):
    size = len(dataloader.dataset)
    num_batches = len(dataloader)
    model.eval()
    test_loss, correct = 0, 0
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            #print("Tensor X")
            #print(X.shape)
            #print("tensor y")
            #print(y.shape)
            pred = model(X)
            test_loss += loss_fn(pred, y).item()
            #correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    test_loss /= num_batches
    #correct /= size
    #print(f"Test Error: \n Accuracy: {(100*correct):>0.1f}%, Avg loss: {test_loss:>8f} \n")
    print(f"Avg loss: {test_loss:>8f} \n")
print('done')

# Training model over 200 epochs
epochs = 200
for t in range(epochs):
    print(f"Epoch {t+1}\n-------------------------------")
    train(train_loader, model, loss_fn, optimizer) # train with training dataloader
    test(val_loader, model, loss_fn) # test with validation dataloader
print("Done!")

# Save the trained model
drive_path = '/content/gdrive/My Drive/Colab Notebooks/'
torch.save(model.state_dict(),drive_path+'kspace_model.pth')
print("Saved PyTorch Model State to model.pth")

# Load the trained model to use it for reconstruction
drive_path = '/content/gdrive/My Drive/Colab Notebooks/'
model = Unet(in_chans=2,
        out_chans=2,
        chans = 32,
        num_pool_layers = 4,
        drop_prob  = 0.0)
model.load_state_dict(torch.load(drive_path+"kspace_model.pth"))

# Evaluate model using testing data
model.eval()
pred = model(test_X)
print('done')

# Need to use the IFFT to change predicted, test, and groundtruth images to image domain for visualization
pred = pred.detach().numpy()
pred_imgs = pred[:,0,:,:]+1j*pred[:,1,:,:]
pred_imgs = [np.fft.ifft2(img) for img in pred_imgs]
test_kspace = test_X.detach().numpy()
test_imgs = test_kspace[:,0,:,:]+1j*test_kspace[:,1,:,:]
test_imgs = [np.fft.ifft2(img) for img in test_imgs]
ground_kspace = test_ground.detach().numpy()
ground_imgs = ground_kspace[:,0,:,:]+1j*ground_kspace[:,1,:,:]
ground_imgs = [np.fft.ifft2(img) for img in ground_imgs]

# Display images for comparison
plt.figure(figsize=(18, n*6))  # Adjust the figure size as needed

for i in range(1, len(pred_imgs)):
    plt.subplot(n, 3, 3*i - 2)  # Use 3*i - 2 to position the subplots correctly
    img_1 = np.abs(ground_imgs[i])
    plt.imshow(img_1, cmap='gray')
    plt.axis('off')  # Turn off axis ticks and labels

    plt.subplot(n, 3, 3*i - 1)  # Use 3*i - 1 to position the subplots correctly
    img_2 = np.abs(test_imgs[i])
    plt.imshow(img_2, cmap='gray')
    plt.axis('off')  # Turn off axis ticks and labels

    plt.subplot(n, 3, 3*i)  # Use 3*i to position the subplots correctly
    img_3 = np.abs(pred_imgs[i])
    plt.imshow(img_3, cmap='gray')
    plt.axis('off')  # Turn off axis ticks and labels

plt.tight_layout()  # Ensure subplots do not overlap
plt.show()

# Calculate average PSNR & SSIM values for the reconstructed image
# compared to the groundtruth image
import skimage
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim
avg_PSNR = 0
avg_SSIM = 0
for i in range(1,len(pred)):
  reImg = np.abs(pred_imgs[i])
  img = np.abs(ground_imgs[i])
  avg_PSNR += psnr(img,reImg,data_range = img.max()-img.min())
  avg_SSIM += ssim(img,reImg)

avg_PSNR = avg_PSNR/len(pred)
avg_SSIM = avg_SSIM/len(pred)

print("Average PSNR is",avg_PSNR)
print("Average SSIM is",avg_SSIM)
