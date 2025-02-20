#! /usr/bin/env python

import sys
from os import path
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

dir_script = path.dirname(path.realpath(__file__))
sys.path.append(dir_script+'/../')
from gcndesign.hypara import HyperParam, InputSource
from gcndesign.dataset import BBGDataset, BBGDataset_fast
from gcndesign.training import train, valid
from gcndesign.models import GCNdesign, weights_init

hypara = HyperParam()
source = InputSource()

# default processing device
source.device = "cuda" if torch.cuda.is_available() else "cpu"

# argument parser
parser = argparse.ArgumentParser()
parser.add_argument('--train_list', '-t', type=str, metavar='[File, File, ...]',
                    help='List of training data.', required=True)
parser.add_argument('--valid_list', '-v', type=str, metavar='[File, File, ...]',
                    help='List of validation data.', required=True)
parser.add_argument('--epochs', '-e', type=int, default=hypara.nepoch, metavar='[Int]',
                    help='Number of training epochs. (default:{})'.format(hypara.nepoch))
parser.add_argument('--learning-rate', '-lr', type=float, default=hypara.learning_rate, metavar='[Float]',
                    help='Learning rate. (default:{})'.format(hypara.learning_rate))
parser.add_argument('--only-predmodule', action='store_true',
                    help=argparse.SUPPRESS)
parser.add_argument('--param-prefix', '-p', type=str, default=source.param_prefix, metavar='[File]',
                    help='Trained parameter prefix. (default:"'+source.param_prefix+'")')
parser.add_argument('--param-in', type=str, default=source.param_in, metavar='[File]',
                    help='Pre-trained parameter file. (default:{})'.format(source.param_in))
parser.add_argument('--checkpoint-in', type=str, default=None, metavar='[File]',
                    help='Checkpoint file. (default:{})'.format(None))
parser.add_argument('--output', '-o', type=str, default=source.file_out, metavar='[File]',
                    help='Output file. (default:"'+source.file_out+'")')
parser.add_argument('--device', type=str, default=source.device, choices=['cpu', 'cuda'],
                    help='Processing device (default:\'cuda\' if available).')
parser.add_argument('--dataloader', type=str, default='slow-HDD', choices=['slow-HDD', 'fast-RAM'],
                    help='DataLoader type.(default:{})'.format('slow-HDD'))

parser.add_argument('--dim-hidden-node0', '-dn0', type=int, default=hypara.d_embed_h_node0, metavar='[Int]',
                    help='Hidden dimentions of the first note-embedding layers. (default:{})'.format(hypara.d_embed_h_node0))
parser.add_argument('--layer-embed-node0', '-ln0', type=int, default=hypara.nlayer_embed_node0, metavar='[Int]',
                    help='Number of the first note-embedding layers. (default:{})'.format(hypara.nlayer_embed_node0))

parser.add_argument('--iter-gcn', '-ig', type=int, default=hypara.niter_embed_rgc, metavar='[Int]',
                    help='Number of iterations of GCN layer. (default:{})'.format(hypara.niter_embed_rgc))
parser.add_argument('--knode-gcn', '-kn', type=int, default=hypara.k_node_rgc, metavar='[Int]',
                    help='Additional dimension of node info. for each GCN update. (default:{})'.format(hypara.k_node_rgc))
parser.add_argument('--kedge-gcn', '-ke', type=int, default=hypara.k_edge_rgc, metavar='[Int]',
                    help='Additional dimension of edge info. for each GCN update. (default:{})'.format(hypara.k_edge_rgc))
parser.add_argument('--dim-hidden-node', '-dn', type=int, default=hypara.d_embed_h_node, metavar='[Int]',
                    help='Hidden dimentions of the note-embedding layers. (default:{})'.format(hypara.d_embed_h_node))
parser.add_argument('--dim-hidden-edge', '-de', type=int, default=hypara.d_embed_h_edge, metavar='[Int]',
                    help='Hidden dimentions of the note-embedding layers. (default:{})'.format(hypara.d_embed_h_node))
parser.add_argument('--layer-embed-node', '-ln', type=int, default=hypara.nlayer_embed_node, metavar='[Int]',
                    help='Number of the note-embedding layers. (default:{})'.format(hypara.nlayer_embed_node))
parser.add_argument('--layer-embed-edge', '-le', type=int, default=hypara.nlayer_embed_edge, metavar='[Int]',
                    help='Number of the edge-embedding layers. (default:{})'.format(hypara.nlayer_embed_edge))

parser.add_argument('--dim-hidden-pred1', '-dp1', type=int, default=hypara.d_pred_h1, metavar='[Int]',
                    help='Hidden dimentions of the prediction layer 1. (default:{})'.format(hypara.d_pred_h1))
parser.add_argument('--dim-hidden-pred2', '-dp2', type=int, default=hypara.d_pred_h2, metavar='[Int]',
                    help='Hidden dimentions of the prediction layer 2. (default:{})'.format(hypara.d_pred_h2))
parser.add_argument('--layer-pred', '-lp', type=int, default=hypara.nlayer_pred, metavar='[Int]',
                    help='Number of prediction layers. (default:{})'.format(hypara.nlayer_pred))
parser.add_argument('--fragsize', '-f', type=int, default=hypara.fragment_size, metavar='[Int]',
                    help='Fragment size of prediction module.(default:{})'.format(hypara.fragment_size))

##  arguments  ##
args = parser.parse_args()
hypara.nepoch = args.epochs
hypara.learning_rate = args.learning_rate
source.file_train = args.train_list
source.file_valid = args.valid_list
source.onlypred = args.only_predmodule
source.param_prefix = args.param_prefix
source.file_out = args.output
source.device = args.device
hypara.d_embed_h_node0 = args.dim_hidden_node0
hypara.nlayer_embed_node0 = args.layer_embed_node0
hypara.niter_embed_rgc = args.iter_gcn
hypara.k_node_rgc = args.knode_gcn
hypara.k_edge_rgc = args.kedge_gcn
hypara.d_embed_h_node = args.dim_hidden_node
hypara.d_embed_h_edge = args.dim_hidden_edge
hypara.nlayer_embed_node = args.layer_embed_node
hypara.nlayer_embed_edge = args.layer_embed_edge
hypara.d_pred_h1 = args.dim_hidden_pred1
hypara.d_pred_h2 = args.dim_hidden_pred2
hypara.nlayer_pred = args.layer_pred
hypara.fragment_size = args.fragsize

#  check input
assert path.isfile(source.file_train), "Training data file {:s} was not found.".format(source.file_train)
assert path.isfile(source.file_valid), "Validation data file {:s} was not found.".format(source.file_valid)

# if checkpoint
if args.checkpoint_in != None:
    checkpoint = torch.load(args.checkpoint_in)
    hypara = checkpoint['hyperparams']
    model = GCNdesign(hypara)
    params = model.size()
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(source.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=hypara.learning_rate)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=hypara.nepoch-10, gamma=0.1)
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
    epoch_init = checkpoint['epoch']+1
else:
    ## Model Setup ##
    model = GCNdesign(hypara).to(source.device)
    # weight initialization
    model.apply(weights_init)
    # Network size
    params = model.size()
    epoch_init = 1
    # optimizer & scheduler
    optimizer = torch.optim.Adam(model.parameters(), lr=hypara.learning_rate)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=hypara.nepoch-10, gamma=0.1)

# for transfer learning
if source.onlypred is True:
    assert path.isfile(source.param_in), "Parameter file {:s} was not found.".format(source.param_in)
    model = torch.load(source.param_in, map_location=torch.device(source.device))
    model.prediction.apply(weights_init)

# dataloader setup
train_dataset = BBGDataset(listfile=source.file_train, hypara=hypara) if args.dataloader == 'slow-HDD' else BBGDataset_fast(listfile=source.file_train, hypara=hypara)
valid_dataset = BBGDataset(listfile=source.file_valid, hypara=hypara) if args.dataloader == 'slow-HDD' else BBGDataset_fast(listfile=source.file_valid, hypara=hypara)
train_loader = DataLoader(dataset=train_dataset, batch_size=1, shuffle=True)
valid_loader = DataLoader(dataset=valid_dataset, batch_size=1, shuffle=True)

# loss function
criterion = nn.CrossEntropyLoss().to(source.device)


# training routine
file = open(source.file_out, 'w')
file.write("# Total Parameters : {:.2f}M\n".format(params/1000000))
for iepoch in range(epoch_init, hypara.nepoch):
    loss_train, acc_train, loss_valid, acc_valid = float('inf'), 0, float('inf'), 0
    # training
    loss_train, acc_train = train(model, criterion, source, train_loader, optimizer, hypara)
    # validation
    loss_valid, acc_valid = valid(model, criterion, source, valid_loader)
    scheduler.step()
    file.write(' {epoch:3d}  LossTR: {loss_TR:.3f} AccTR: {acc_TR:.3f}  LossTS: {loss_TS:.3f} AccTS: {acc_TS:.3f}\n'
                .format(epoch=iepoch, loss_TR=loss_train, acc_TR=acc_train, loss_TS=loss_valid, acc_TS=acc_valid))
    file.flush()
    # output params
    torch.save(model, "{}-{:03d}.pkl".format(source.param_prefix, iepoch))
    torch.save({
        'epoch': iepoch,
        'model_state_dict': model.to('cpu').state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'loss': loss_train,
        'hyperparams': hypara
    }, "{}-{:03d}.ckp".format(source.param_prefix, iepoch))
    model.to(source.device)