import json
from pydub import AudioSegment # https://github.com/jiaaro/pydub/
import pandas as pd
import argparse
import os
from tqdm import trange



def convertToTSV(jsonFile):
    with open(jsonFile) as f:
        a = json.load(f)
        return a


def main(args):
    # make my life easier just assume
    # first arg is the json
    # second is the full mp3 audio
    # third is the fold to store the audio splits
    # forth is the output file name

    a = convertToTSV(args.jsonIn)
    audio = AudioSegment.from_mp3(args.audioIn)
    # create the same structure as the example tsv except client id
    tsvOut = {'path':[], 'sentence':[]}

    startTimeMS = -1 # -1 indicates we need the start index
    endTimeMS = -1
    transcript = ''
    j = 0 # sentence count

    # now loop over the segments
    for i in trange(len(a['results']['segments'])):
        # amazon gives alternative trannscriptions
        # i'm just going to take the first
        # then I'll get the start and end times for this segment

        
        items = a['results']['segments'][i]['alternatives'][0]['items']
        for endIndex in range(len(items)):
            
            # append the content to the transcription
            if 'punctuation' not in items[endIndex]:
                transcript = transcript + items[endIndex]['content'] + ' '
            else:
                transcript = transcript + items[endIndex]['content']

            # get the first index
            if startTimeMS == -1 and 'start_time' in items[endIndex]:
                startTimeMS = 1000*float(items[endIndex]['start_time'])
                continue

            if 'end_time' in items[endIndex]:
                # always update
                endTimeMS = 1000*float(items[endIndex]['end_time'])

            if 'end_time' not in items[endIndex]:
                # then we reached end of a sentence
                # now split the audio and save it out in format for deepspeech
                audioSeg = audio[startTimeMS:endTimeMS]
                # write out audio 16kHz wav 
                audioSeg.export(f'{args.audioOut}{os.sep}segment{i}_{j}.wav', format='wav', parameters=['-ar', '16000'])
                startTimeMS = -1 # need to find the next start time

                # and now add a line to the tsv
                tsvOut['path'].append(f'{args.audioOut}{os.sep}segment{i}_{j}.wav')
                tsvOut['sentence'].append(transcript)
                j = j + 1
                transcript = ''


    pd.DataFrame(tsvOut).to_csv(args.tsvOut,sep='\t',index=False)

if __name__ == '__main__':
    # for example
    # create a folder called segments inside the directory with 
    # python tsvcreator.py -i ../data/452020.mp3 -j ../data/asrOutput.json -o ./segments -t deepspeech.tsv
    parser = argparse.ArgumentParser(description='convert audio to tsv and split into segments for DeepSpeech.')
    parser.add_argument('-i', action='store', help='Audio input mp3 file', dest='audioIn')
    parser.add_argument('-j', action='store', help='json trascription file input from aws', dest='jsonIn')
    parser.add_argument('-o', action='store', help='The folder to store the audio segments', dest='audioOut', default='')
    parser.add_argument('-t', action='store', help='The file to store the deepSpeech tsv file', dest='tsvOut')

    args = parser.parse_args()
    main(args)
