#! /usr/bin/env python

import sys
from os import path
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

dir_script = path.dirname(path.realpath(__file__))
sys.path.append(dir_script+'/../')
from gcndesign.hypara import HyperParam, InputSource
from gcndesign.dataset import BBGDataset, BBGDataset_fast
from gcndesign.training import train, valid
from gcndesign.models import GCNdesign, weights_init
from gcndesign.radam import RAdam

hypara = HyperParam()
source = InputSource()

# default processing device
source.device = "cuda" if torch.cuda.is_available() else "cpu"

# argument parser
parser = argparse.ArgumentParser()
parser.add_argument('--train-list', '-t', type=str, default=source.file_train, metavar='[File]',
                    help='List of training data.', required=True)
parser.add_argument('--valid-list', '-v', type=str, default=source.file_valid, metavar='[File]',
                    help='List of validation data.', required=True)
parser.add_argument('--epochs', type=int, default=hypara.nepoch, metavar='[Int]',
                    help='Number of training epochs. (default:{})'.format(hypara.nepoch))
parser.add_argument('--lr', type=float, default=hypara.learning_rate, metavar='[Float]',
                    help='Learning rate. (default:{})'.format(hypara.learning_rate))
parser.add_argument('--only-predmodule', action='store_true',
                    help=argparse.SUPPRESS)
parser.add_argument('--param-out', '-p', type=str, default=source.param_out, metavar='[File]',
                    help='Trained parameter file. (default:"'+source.param_out+'")')
parser.add_argument('--param-in', type=str, default=source.param_in, metavar='[File]',
                    help='Pre-trained parameter file. (default:{})'.format(source.param_in))
parser.add_argument('--output', '-o', type=str, default=source.file_out, metavar='[File]',
                    help='Output file. (default:"'+source.file_out+'")')
parser.add_argument('--device', type=str, default=source.device, choices=['cpu', 'cuda'],
                    help='Processing device.')
parser.add_argument('--layer', type=int, default=hypara.niter_embed_rgc, metavar='[Int]',
                    help='Number of GCN layers. (default:{})'.format(hypara.niter_embed_rgc))
parser.add_argument('--fragsize', type=int, default=hypara.fragment_size, metavar='[Int]',
                    help='Fragment size of prediction module.(default:{})'.format(hypara.fragment_size))
parser.add_argument('--dataloader', type=str, default='slow-HDD', choices=['slow-HDD', 'fast-RAM'],
                    help='DataLoader type.(default:{})'.format('slow-HDD'))

##  arguments  ##
args = parser.parse_args()
hypara.nepoch = args.epochs
hypara.learning_rate = args.lr
source.file_train = args.train_list
source.file_valid = args.valid_list
source.onlypred = args.only_predmodule
source.param_out = args.param_out
source.file_out = args.output
source.device = args.device
hypara.niter_embed_rgc = args.layer
hypara.fragment_size = args.fragsize

## Model Setup ##
model = Network(hypara).to(source.device)
# weight initialization
model.apply(weights_init)
# Network size
params = model.size()


## Training ##
#  check input
assert path.isfile(source.file_train), "Training data file {:s} was not found.".format(source.file_train)
assert path.isfile(source.file_valid), "Validation data file {:s} was not found.".format(source.file_valid)
        
# for transfer learning
if source.onlypred is True:
    assert path.isfile(source.param_in), "Parameter file {:s} was not found.".format(source.param_in)
    model.load_state_dict(torch.load(source.param_in, map_location=torch.device(source.device)), strict=True)
    model.prediction.apply(weights_init)

# dataloader setup
train_dataset = BBGDataset(listfile=source.file_train, hypara=hypara) if args.dataloader == 'slow-HDD' else BBGDataset_fast(listfile=source.file_train, hypara=hypara)
valid_dataset = BBGDataset(listfile=source.file_valid, hypara=hypara) if args.dataloader == 'slow-HDD' else BBGDataset_fast(listfile=source.file_valid, hypara=hypara)
train_loader = DataLoader(dataset=train_dataset, batch_size=1, shuffle=True)
valid_loader = DataLoader(dataset=valid_dataset, batch_size=1, shuffle=True)

# loss function
criterion = nn.CrossEntropyLoss().to(source.device)

# optimizer setup
optimizer = RAdam(model.parameters(), lr=hypara.learning_rate)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=hypara.nepoch-10, gamma=0.1)

# training routine
file = open(source.file_out, 'w')
file.write("# Total Parameters : {:.2f}M\n".format(params/1000000))
loss_min = float('inf')
for iepoch in range(hypara.nepoch):
    loss_train, acc_train, loss_valid, acc_valid = float('inf'), 0, float('inf'), 0
    # training
    loss_train, acc_train = train(model, criterion, source, train_loader, optimizer, hypara)
    # validation
    loss_valid, acc_valid = valid(model, criterion, source, valid_loader)
    scheduler.step()
    file.write(' {epoch:3d}  LossTR: {loss_TR:.3f} AccTR: {acc_TR:.3f}  LossTS: {loss_TS:.3f} AccTS: {acc_TS:.3f}\n'
                .format(epoch=iepoch+1, loss_TR=loss_train, acc_TR=acc_train, loss_TS=loss_valid, acc_TS=acc_valid))
    file.flush()
    # output params
    if(loss_min > loss_valid):
        torch.save(model.state_dict(), source.param_out)
        loss_min = loss_valid

