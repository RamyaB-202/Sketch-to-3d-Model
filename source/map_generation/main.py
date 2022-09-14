import os.path

import map_generation
import warnings
import argparse
from pytorch_lightning.trainer import Trainer
from pytorch_lightning.loggers import TensorBoardLogger
import torch
from torch.utils.data import DataLoader
import torch.utils.data as data
import dataset_generation.DataSet as DataSet
from pytorch_lightning.callbacks import ModelCheckpoint

def run(train, input_dir, target_dir, output_path,
        type, epochs, lr, batch_size, n_critic, weight_L1, weight_BCELoss,
        use_generated_model=False, generated_model_path="", use_comparison=True):


    if len(input_dir) <= 0 or len(target_dir) <= 0 or not os.path.exists(input_dir) or not os.path.exists(target_dir):
        raise RuntimeError("Input and Target image dirs are not given or do not exist!")

    if type == "depth":
        given_type = map_generation.Type.depth
    elif type == "normal":
        given_type = map_generation.Type.normal
    else:
        raise RuntimeError("Given type should either be \"normal\" or \"depth\"!")

    if len(output_path) <= 0:
        raise RuntimeError("Output Path is not given!")
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    model = map_generation.MapGen(given_type, n_critic, weight_L1, weight_BCELoss, use_comparison, output_path, lr)
    if use_generated_model:
        if not os.path.exists(generated_model_path):
            raise RuntimeError("Generated model paths are not given!")
        model.load_from_checkpoint(generated_model_path)


    checkpoint_callback = ModelCheckpoint(
        save_top_k=10,
        save_last=True,
        monitor="val_loss",
        mode="min",
        dirpath=output_path,
        filename="MapGen-{epoch:02d}-{val_loss:.2f}",
    )
    logger = TensorBoardLogger("tb_logs", name="trainModel")
    dataSet = DataSet.DS(input_dir, target_dir, given_type)
    trainer = Trainer(gpus=0 if torch.cuda.is_available() else 0,
                      max_epochs=epochs,
                      callbacks=[checkpoint_callback],
                      logger=logger)
    if train:
        train_set_size = int(len(dataSet) * 0.8)
        valid_set_size = len(dataSet) - train_set_size
        seed = torch.Generator().manual_seed(42)
        train_set, valid_set = data.random_split(dataSet, [train_set_size, valid_set_size], seed)
        dataloader_train = DataLoader(train_set, batch_size=batch_size,
                                shuffle=True, num_workers=4)
        dataloader_vaild = DataLoader(valid_set, batch_size=batch_size,
                                shuffle=False, num_workers=4)
        trainer.fit(model, dataloader_train)

    else:
        if not use_generated_model:
            warnings.warn("Map generation is called on untrained models!")
        dataloader = DataLoader(dataSet, batch_size=1,
                                shuffle=False, num_workers=0)
        trainer.test(model, dataloaders=dataloader)


def diff_args(args):
    run(args.train,
        args.input_dir,
        args.target_dir,
        args.output_dir,
        args.type,
        args.epochs,
        args.lr,
        args.batch_size,
        args.n_critic,
        args.weight_L1,
        args.weight_BCELoss,
        args.use_generated_model,
        args.generated_model_path,
        args.use_comparison)

def main(args):
    parser = argparse.ArgumentParser(prog="dataset_generation")
    parser.add_argument("--train", type=bool, default=True, help="Train or test")
    parser.add_argument("--input_dir", type=str, default="..\\..\\resources\\sketch_meshes", help="Directory where the input sketches for training are stored")
    parser.add_argument("--target_dir", type=str, default="..\\..\\resources\\n_meshes", help="Directory where the normal or depth maps for training are stored")
    parser.add_argument("--output_dir", type=str, default="..\\..\\output", help="Directory where the checkpoints or the test output is stored")
    parser.add_argument("--type", type=str, default="normal", help="use \"normal\" or \"depth\" in order to train\\generate depth or normal images")
    parser.add_argument("--epochs", type=int, default=100, help="# of epoch")
    parser.add_argument("--lr", type=float, default=100, help="initial learning rate")
    parser.add_argument("--batch_size", type=int, default=1, help="# of epoch")
    parser.add_argument("--n_critic", type=int, default=5, help="# of n_critic")
    parser.add_argument("--weight_L1", type=int, default=500, help="L1 weight")
    parser.add_argument("--weight_BCELoss", type=int, default=100, help="L1 weight")
    parser.add_argument("--use_generated_model", type=bool, default=False, help="If models are trained from scratch or already trained models are used")
    parser.add_argument("--generated_model_path", type=str, default="..\\..\\output\\test.ckpt", help="If test is used determine if comparison images should be generated")
    parser.add_argument("--use_comparison", type=bool, default=True, help="If test is used determine if comparison images should be generated")
    args = parser.parse_args(args)
    diff_args(args)

if __name__ == '__main__':
    params = [
        '--input_dir', '..\\..\\output\\sketch_mapgen',
        '--target_dir', '..\\..\\output\\n_mapgen',
        '--output_dir', '..\\..\\checkpoints',
        '--type', 'normal',
        '--epochs', '100',
        '--lr', '0.2'
    ]
    main(params)