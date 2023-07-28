# ESE-Capstone
ESE 498 Capstone Design Project: Convolutional Neural Network for 2-D MRI Image Reconstruction in k-space

Deep learning algorithms, such as convolutional neural networks (CNNs), are powerful tools for accelerating brain magnetic resonance imaging (MRI) image reconstruction, greatly improving the imaging process for patients and healthcare workers.  We use the U-net architecture – a CNN architecture – to reconstruct: (1) a 2-D MRI brain image from a zero-filled image in the image domain and (2) a 2-D MRI brain image from a zero-filled image in k-space.  We use images from the Brain Dataset from Aggarwal et al. [1-2] to train and evaluate our model.  We assess the quality of the reconstructed images from each task using average PSNR and SSIM.  Image reconstruction in the image domain yielded an average PSNR and SSIM values of  27.50 dB and 0.7855, respectively.  For image reconstruction in k-space, we obtained an average PSNR value of 28.59 dB and an average SSIM of 0.7050.  

**Capstone Proposal.pdf** Formal Proposal

**finalreport** Final Report

**website** Link to website

**poster** Poster Presentation

_________________________________________________________________________________________________________________________________
Brain Dataset used to train model comes from Aggarwal et al [1-2].

[1] H.K. Aggarwal, M.P. Mani, and M. Jacob, “MoDL: Model Based Deep Learning   Architecture for Inverse Problems,” 2019. [Online serial]. Available:          https://arxiv.org/abs/1712.02862. [Accessed Feb. 7, 2023].

[2] H.K. Aggarwal, M.P. Mani, and M. Jacob, “Brain Dataset,” Github: hkaggarwal/modl, 2019. 
    Available: https://drive.google.com/file/d/1qp-l9kJbRfQU1W5wCjOQZi7I3T6jwA37/view. [Accessed Dec. 2, 2022].
_________________________________________________________________________________________________________________________________
**2D Reconstruction in Image Domain:**

**2Dimgdomain.py** code for processing images, training and testing the model can also be found at https://colab.research.google.com/drive/1bNoooVbWXfAZ0spEPPeJbew0ZSh4AzUP?usp=sharing

**imgdomain.png** Side by side comparison of the groundtruth, zero-filled, and reconstructed images

**pretrained model:** https://drive.google.com/file/d/1SRvze0oMrmj8ibgZkJCD0ktEUfuP5Kwo/view?usp=sharing

_________________________________________________________________________________________________________________________________

**2D Reconstruction in k-space:**

**2Dkspace.py** code for processing images, training and testing the model can also be found at https://colab.research.google.com/drive/1jn9l0XWK0cVUv162y6iJMJhbiZJy23t6#scrollTo=HY-MdiMhhdVK

**kspace_images.png** Side by side comparison of the groundtruth, zero-filled, and reconstructed images

**pretrained model:** https://drive.google.com/file/d/1RDadJkXuakQcutRQq0__EX9WqNN975IS/view?usp=sharing
