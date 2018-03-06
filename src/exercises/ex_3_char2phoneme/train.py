from char2phoneme_model import Char2Phoneme
from data import load_data
import resources as R

from random import shuffle, sample

import tensorflow as tf
import numpy as np

from tqdm import tqdm

PAD = 0


def seq_maxlen(seqs):
    """
    Maximum length of max-length sequence 
     in a batch of sequences
    Args:
        seqs : list of sequences
    Returns:
        length of the lengthiest sequence
    """
    return max([len(seq) for seq in seqs])

def pad_seq(seqs, maxlen=0, PAD=PAD, truncate=False):

    # pad sequence with PAD
    #  if seqs is a list of lists
    if type(seqs[0]) == type([]):

        # get maximum length of sequence
        maxlen = maxlen if maxlen else seq_maxlen(seqs)

        def pad_seq_(seq):
            if truncate and len(seq) > maxlen:
                # truncate sequence
                return seq[:maxlen]

            # return padded
            return seq + [PAD]*(maxlen-len(seq))

        seqs = [ pad_seq_(seq) for seq in seqs ]
    
    return seqs

def vectorize_batch(batch):
    return {
        'chars'    : np.array([ ch for ch,ph in batch ]),
        'phonemes' : np.array([ ph for ch,ph in batch ])
    }

def train_model(model, trainset, testset, batch_size=200, max_acc=.90):
    epochs = 100
    iterations = len(trainset)//batch_size

    # fetch default session
    sess = tf.get_default_session()
    
    try:
        for j in range(epochs):
            loss = []
            for i in tqdm(range(iterations)):
                # fetch next batch
                batch = vectorize_batch(trainset[i*batch_size : (i+1)*batch_size])
                _, out = sess.run([ model.trainop,  model.out ],
                        feed_dict = {
                            model.placeholders['chars']  : batch['chars'],
                            model.placeholders['phonemes' ]  : batch['phonemes' ],
                            }
                        )
                loss.append(out['loss'])

            print('<train> [{}]th epoch : loss : {}'.format(j, np.array(out['loss']).mean()))
            # evaluate and calc accuracy
            accuracy = evaluate(model, testset)
            print('\t<eval > accuracy : {}'.format(accuracy))

            if accuracy >= max_acc :
                print('<train> accuracy > MAX_ACC; Exit training...')
                return

    except KeyboardInterrupt:
        accuracy = evaluate(model, testset)
        print('<train> Forced Interrupt...')
        print('\t<eval > accuracy : {}'.format(accuracy))
        return

def evaluate(model, testset, batch_size=32):
    iterations = len(testset)//batch_size

    # fetch default session
    sess = tf.get_default_session()

    accuracy = []
    for i in range(iterations):
        # fetch next batch
        batch = vectorize_batch(testset[i*batch_size : (i+1)*batch_size])
        out = sess.run(model.out,
                feed_dict = {
                    model.placeholders['chars']  : batch['chars' ],
                    model.placeholders['phonemes' ]  : batch['phonemes'  ]
                    }
                )
        accuracy.append(out['accuracy'])

    return np.array(accuracy).mean()

def predict(model, batch, top_k=3):
    sess = tf.get_default_session()
    return sess.run(model.out,
            feed_dict = {
                model.placeholders['chars']  : batch['chars' ],
                model.placeholders['phonemes' ]  : batch['phonemes'  ]
                }
            )['pred']

def idx2str(indices, lookup, delimiter=''):
    return delimiter.join([ lookup.get(i) for i in indices if i ])

def interact(model, validset, char_lookup, phoneme_lookup, n=3):

    print('\n<interact>\n\n')
    #ui = 'y'
    while input() is not 'q':
        samples = sample(validset, n)
        preds = predict(model, vectorize_batch(samples))
        for pred, (chars, phonemes) in zip(preds, samples):
            print('{} : {} / {}'.format(
                idx2str(chars, char_lookup),
                idx2str(pred, phoneme_lookup, '_'),
                idx2str(phonemes, phoneme_lookup, '_')
                ))

if __name__ == '__main__':

    data_ctl, phonemes, chars = load_data()

    samples = [ (ch, ph) for ch,ph in zip(chars, phonemes) ]
    shuffle(samples)
    trainlen = int(len(samples)*0.80)
    testlen  = int(len(samples)*0.10)
    validlen = testlen
    # split
    len_sorted = lambda l : sorted(l, key=lambda x : len(x[0]))
    trainset = len_sorted(samples[:trainlen])
    testset  = len_sorted(samples[trainlen:trainlen + testlen])
    validset = len_sorted(samples[trainlen + testlen : ])

    seqlen = data_ctl.get('limit').get('maxph')
    idx2alpha, idx2pho = data_ctl['idx2alpha'], data_ctl['idx2pho']

    model = Char2Phoneme(
            emb_dim = 150, 
            char_vocab_size    = len(idx2alpha),
            phoneme_vocab_size =   len(idx2pho),
            seqlen = seqlen
            )

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        train_model(model, trainset, testset, batch_size=128, max_acc=0.70)
        interact(model, validset, vocab)
