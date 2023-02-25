# Sketch23D - Masterthesis Kerstin Hofer

This repositiory contains the [latex code](latex_code) of this thesis and the [paper](paper) used for research. The input used for the evaluation and the respective output files are privided in [data](data).
Futhermore, the [source code](source) as well as [utility code](util), which includes information and instructions regarding the setup and comparison sources, is provided.

## Installation
The provided source code works on both windows 10 and 11 as well as linux Ubuntu 22.04. The required python packages can be installed via Anaconda using the conda requirements ([linux](util/environment_setup/conda_requirements_linux.txt) or [windows](util/environment_setup/conda_requirements_windows.txt)).
A version of NVIDA CUDA (preferrably NVIDA CUDA 11.4 for windows or 11.5 for linux) is required, refer to [the NVIDIA website](https://developer.nvidia.com/cuda-toolkit) for information on the installation.

## Datasets
To create the datasets from scratch follow the instructions in [util/dataset_ShapeNet](util/dataset_ShapeNet) and [util/dataset_Thingy10k_ABC](util/dataset_Thingy10k_ABC) respectively.

## Comparion Code (Neural Mesh Renderer)
The state-of-the-art code used for comparison is the [Neural Mesh Renderer](https://arxiv.org/pdf/1711.07566.pdf) introduced by Kato, Ushiku, and Harada 2018. The instructions to recreate the 
adapted setup used in this thesis is described in [util/NMR](util/NMR).