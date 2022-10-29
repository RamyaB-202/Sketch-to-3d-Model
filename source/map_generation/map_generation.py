import os
import torch
import pytorch_lightning as pl
import numpy as np
from PIL import Image
import torchvision

from generator import Generator
from discriminator import Discriminator
from source.util import OpenEXR_utils
from source.util import data_type

class MapGen(pl.LightningModule):
    def __init__(self, data_type, n_critic, batch_size, weight_L1, gradient_penalty_coefficient, output_dir, lr):
        super(MapGen, self).__init__()
        self.save_hyperparameters()
        self.data_type = data_type
        self.G = Generator(self.channel)
        self.D = Discriminator(self.channel)
        self.n_critic = n_critic
        self.batch_size = batch_size
        self.weight_L1 = weight_L1
        self.output_dir = output_dir
        self.lr = lr
        self.L1 = torch.nn.L1Loss()
        self.gradient_penalty_coefficient = gradient_penalty_coefficient

    @property
    def channel(self):
        if self.data_type == data_type.Type.depth:
            return 1
        else:
            return 3


    def configure_optimizers(self):
        opt_g = torch.optim.RMSprop(self.G.parameters(), lr=(self.lr or self.learning_rate))
        opt_d = torch.optim.RMSprop(self.D.parameters(), lr=(self.lr or self.learning_rate))

        return [{'optimizer': opt_g, 'frequency': 1},
                {'optimizer': opt_d, 'frequency': self.n_critic}]


    def forward(self, sample_batched):
        x = sample_batched['input']
        return self.G(x)

    def generator_step(self, sample_batched, fake_images):
        print("Generator")
        input_predicted = torch.cat((sample_batched['input'], fake_images), 1)
        pred_false = self.D(input_predicted)
        d_loss_fake = torch.mean(pred_false)
        pixelwise_loss = self.L1(fake_images, sample_batched['target'])
        g_loss = -d_loss_fake + pixelwise_loss * self.weight_L1
        self.log("g_Loss", float(g_loss.item()), on_epoch=True, prog_bar=True, logger=True, batch_size=self.batch_size)
        return g_loss

    def gradient_penalty(self, real_images, fake_images):
        alpha = torch.rand((real_images.size(0), 1, 1, 1)).to(real_images.device)
        alpha = alpha.expand_as(real_images)
        interpolation = alpha * real_images + ((1 - alpha) * fake_images).requires_grad_(True)
        d_interpolated = self.D(interpolation)
        gradients = torch.autograd.grad(
            outputs=d_interpolated,
            inputs=interpolation,
            grad_outputs=torch.ones_like(d_interpolated),
            create_graph=True,
            retain_graph=True,
        )[0]
        gradients = gradients.view(real_images.size(0), -1)
        grad_norm = gradients.norm(2, 1)
        return torch.mean((grad_norm - 1) ** 2)
    def compute_gradient_penalty(self, real_samples, fake_samples):
        alpha = torch.Tensor(np.random.random((real_samples.size(0), 1, 1, 1))).to(self.device)
        interpolates = (alpha * real_samples + ((1 - alpha) * fake_samples)).requires_grad_(True)
        interpolates = interpolates.to(self.device)
        d_interpolates = self.D(interpolates)
        fake = torch.Tensor(real_samples.shape[0], 1).fill_(1.0).to(self.device)
        gradients = torch.autograd.grad(
            outputs=d_interpolates,
            inputs=interpolates,
            grad_outputs=fake,
            create_graph=True,
            retain_graph=True,
            only_inputs=True,
        )[0]
        gradients = gradients.view(gradients.size(0), -1).to(self.device)
        gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean()
        return gradient_penalty

    def discriminator_step(self, sample_batched, fake_images):
        print("Discriminator")
        input_predicted = torch.cat((sample_batched['input'], fake_images), 1)
        pred_false = self.D(input_predicted.detach())
        d_loss_fake = torch.mean(pred_false)
        # train discriminator on real images
        input_target = torch.cat((sample_batched['input'], sample_batched['target']), 1)
        pred_true = self.D(input_target)
        d_loss_real = torch.mean(pred_true)
        gradient_penalty = self.gradient_penalty(input_target, input_predicted)

        # loss as defined by Wasserstein paper
        d_loss = -d_loss_real + d_loss_fake + self.gradient_penalty_coefficient * gradient_penalty
        self.log("d_loss", float(d_loss.item()), on_epoch=True, prog_bar=True, logger=True, batch_size=self.batch_size)
        self.log("d_loss_real", float(d_loss_real.item()), on_epoch=True, prog_bar=True, logger=True, batch_size=self.batch_size)
        self.log("d_loss_fake", float(d_loss_fake.item()), on_epoch=True, prog_bar=True, logger=True, batch_size=self.batch_size)

        return d_loss

    def training_step(self, sample_batched, batch_idx, optimizer_idx):
        fake_images = self(sample_batched)
        if optimizer_idx == 0:
            loss = self.generator_step(sample_batched, fake_images)

        elif optimizer_idx == 1:
            loss = self.discriminator_step(sample_batched, fake_images)
        return loss

    def validation_step(self, sample_batched, batch_idx):
        predicted_image = self(sample_batched)
        pixelwise_loss = self.L1(predicted_image, sample_batched['target'])
        self.log("val_loss", pixelwise_loss.item(), batch_size=self.batch_size)
        target_norm = (sample_batched['target']+1)/2
        predicted_list = predicted_image[:6]
        transformed_images = []
        target_list = target_norm[:6]
        for i in range(len(predicted_list)):
            curr_pred = predicted_list[i]
            curr_target = target_list[i]
            i_norm = (curr_pred+1.0) / 2
            pred_target = torch.cat((i_norm, curr_target), 1)
            transformed_images.append(pred_target)

        grid = torchvision.utils.make_grid(transformed_images)
        logger = self.logger.experiment
        image_name_pred = str(self.global_step) + "generated_and_target_images"
        logger.add_image(image_name_pred, grid, 0)

    def test_step(self, sample_batched, batch_idx):
        predicted_image = self(sample_batched)
        predicted_image_norm = (predicted_image+1.0)*127.5
        target_image_norm = (sample_batched['target']+1.0)*127.5
        imagename = sample_batched['input_path'][0].rsplit("/", 1)[-1].split("_", 1)[0]
        OpenEXR_utils.writeRGBImage(predicted_image, self.data_type, os.path.join(self.output_dir, imagename + "_normal.exr"))
        comp = torch.cat((predicted_image_norm, target_image_norm), 3)
        img = Image.fromarray(torch.squeeze(comp).int().cpu().numpy().astype(np.uint8).transpose(1, 2, 0))
        image_path = os.path.join(self.output_dir, imagename + ".png")
        img.save(image_path)
