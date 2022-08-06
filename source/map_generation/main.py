import map_generation
import torch
import source.util.save_load_networks as Save_Load_Network
import argparse

def run(train, use_generated_model, input_dir, target_dir, checkpoint_path="", generated_Gen="", generated_Disc=""):
    if len(input_dir) <= 0 and len(target_dir) <= 0:
        raise RuntimeError("Input and Target image dirs are not given!")

    if train:
        if len(checkpoint_path) <= 0:
            raise RuntimeError("Checkpoint Path is not given!")
        model = map_generation.MapGen(checkpoint_path)
        if use_generated_model:
            if len(generated_Gen) <= 0 and len(generated_Disc) <= 0:
                saved_epoch_gen = Save_Load_Network.load_models(model.G, model.optim_G, generated_Gen)
                print("Generator previously trained for " + str(saved_epoch_gen) + "epochs!")
                saved_epoch_disc = Save_Load_Network.load_models(model.D, model.optim_D, generated_Disc)
                print("Discriminator previously trained for " + str(saved_epoch_gen) + "epochs!")
                if saved_epoch_gen != saved_epoch_disc:
                    raise RuntimeError("Epochs of given models are not the same!")
            else:
                raise RuntimeError("Generated model paths are not given!")
        model.train(input_dir, target_dir)


def diff_args(args):
    run(args.train, args.use_generated_model, args.input_dir, args.target_dir, args.generated_Gen, args.generated_Disc)

def main(args):
    parser = argparse.ArgumentParser(prog="dataset_generation")
    parser.add_argument("--train", type=bool, help="If models are trained")
    parser.add_argument("--use_generated_model", type=bool, help="If models are trained from scratch or already trained models are used")
    parser.add_argument("--input_dir", type=bool, help="Directory where the input sketches for training are stored")
    parser.add_argument("--target_dir", type=bool, help="Directory where the normal or depth maps for training are stored")
    parser.add_argument("--checkpointPath", type=str, help="Directory where the normal or depth maps for training are stored")
    parser.add_argument("--generated_Gen", type=str, help="Directory where the normal or depth maps for training are stored")
    parser.add_argument("--generated_Disc", type=str, help="Directory where the normal or depth maps for training are stored")
    args = parser.parse_args(args)
    diff_args(args)

if __name__ == '__main__':
    params = [
        '--train', True,
        '--use_generated_model', False,
        '--input_dir', "../../resources/sketch_meshes",
        '--target_dir', "../../resources/n_meshes"
        '--checkpoint_path', "../../checkpoints"
    ]
    main(params)