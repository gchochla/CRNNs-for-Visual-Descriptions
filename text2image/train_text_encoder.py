'''Train text encoder.'''

import os
import argparse

import torch
import torch.optim as optim

from text2image.utils import CUBDataset, encoders_loss
from text2image.encoders import googlenet_feature_extractor, ConvolutionalLSTM

def main():
    '''Main'''

    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--dataset_dir', required=True, type=str,
                        help='dataset root directory')

    parser.add_argument('-avc', '--avail_class_fn', required=True, type=str,
                        help='txt containing classes used')

    parser.add_argument('-i', '--image_dir', required=True, type=str,
                        help='directory of images w.r.t dataset directory')

    parser.add_argument('-t', '--text_dir', required=True, type=str,
                        help='directory of descriptions w.r.t detaset directory')

    parser.add_argument('-px', '--img_px', required=True, type=int,
                        help='pixels for image to be resized to')

    parser.add_argument('-cut', '--text_cutoff', required=True, type=int,
                        help='fixed dimension of tokens of text')

    parser.add_argument('-lvl', '--level', default='char', type=str, choices=['char', 'word'],
                        help='level of temporal resolution')

    parser.add_argument('-v', '--vocab_fn', type=str,
                        help='vocabulary filename w.r.t dataset directory.' + \
                            'Used only when level=word')

    parser.add_argument('-ch', '--conv_channels', nargs='*', type=int, required=True,
                        help='convolution channels')

    parser.add_argument('-k', '--conv_kernels', nargs='*', type=int, required=True,
                        help='convolution kernel sizes')

    parser.add_argument('-rn', '--rnn_num_layers', type=int, required=True,
                        help='number of layers in rnn')

    parser.add_argument('-m', '--conv_maxpool', type=int, default=3,
                        help='maxpool parameter')

    parser.add_argument('-cd', '--conv_dropout', type=float,
                        help='dropout in convolutional layers')

    parser.add_argument('-rd', '--rnn_dropout', type=float,
                        help='dropout in lstm cells')

    parser.add_argument('-rb', '--rnn_bidir', default=False, action='store_true',
                        help='whether to use bidirectional rnn')

    parser.add_argument('-b', '--batches', required=True, type=int,
                        help='number of batches')

    parser.add_argument('-lr', '--learning_rate', type=float, default=1e-4,
                        help='learning rate')

    parser.add_argument('-mfn', '--model_fn', type=str, help='where to save model\'s parameters')

    args = parser.parse_args()

    trainset = CUBDataset(dataset_dir=args.dataset_dir, avail_class_fn=args.avail_class_fn,
                          image_dir=args.image_dir, text_dir=args.text_dir, img_px=args.img_px,
                          text_cutoff=args.text_cutoff, level=args.level, vocab_fn=args.vocab_fn)

    img_encoder = googlenet_feature_extractor().eval()
    txt_encoder = ConvolutionalLSTM(vocab_dim=trainset.vocab_len, conv_channels=args.conv_channels,
                                    conv_kernels=args.conv_kernels, conv_maxpool=args.conv_maxpool,
                                    rnn_num_layers=args.rnn_num_layers, rnn_bidir=args.rnn_bidir,
                                    conv_dropout=args.conv_dropout, rnn_dropout=args.rnn_dropout,
                                    rnn_hidden_size=1024 if not args.rnn_bidir else 512).train()

    optimizer = optim.Adam(txt_encoder.parameters(), lr=args.lr)

    for batch in range(args.batches):
        print(f'Batch {batch+1}')

        ims, txts, lbls = trainset.get_next_batch()
        img_embs = img_encoder(ims)
        txt_embs = txt_encoder(txts)

        loss = encoders_loss(img_embs, txt_embs, lbls, batched=False)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print('Done training')

    if args.model_fn:
        if not os.path.exists(os.path.split(args.model_fn)[0]):
            os.makedirs(os.path.split(args.model_fn)[0])
        torch.save(txt_encoder.state_dict(), args.model_fn)

if __name__ == '__main__':
    main()