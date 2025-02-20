#! /usr/bin/env python

import sys
from os import path
import argparse
import torch

dir_script = path.dirname(path.realpath(__file__))
sys.path.append(dir_script+'/../')
from gcndesign.predictor import Predictor

# default processing device
device = "cuda" if torch.cuda.is_available() else "cpu"

# argument parser
parser = argparse.ArgumentParser()
parser.add_argument('pdb', type=str, default=None, metavar='[File]',
                    help='PDB file input.')
parser.add_argument('--temperature', '-t', type=float, default=1.0, metavar='[Float]',
                    help='Temperature: probability P(AA) is proportional to exp(logit(AA)/T). (default:{})'.format(1.0))
parser.add_argument('--param-in', '-p', type=str, default=None, metavar='[File]',
                    help='NN parameter file. (default:{})'.format(None))
parser.add_argument('--device', type=str, default=device, choices=['cpu', 'cuda'],
                    help='Processing device. (default:\'cuda\' if available)')
args = parser.parse_args()

# check files
assert path.isfile(args.pdb), "PDB file {:s} was not found.".format(args.pdb)
    
# prediction
predictor = Predictor(device=args.device, param=args.param_in)
pred = predictor.predict(pdb=args.pdb, temperature=args.temperature)

# output
for pdict, info in pred:
    max_key = max(pdict, key=pdict.get)
    print(' %4d %s %s:pred ' % (info['resnum'], info['original'], max_key), end='')
    for aa in pdict.keys():
        print(' %5.3f:%s' % (pdict[aa], aa), end='')
    print('')
