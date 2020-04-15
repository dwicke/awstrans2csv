import json
from pydub import AudioSegment # https://github.com/jiaaro/pydub/
import pandas as pd
import argparse
import os
from tqdm import trange
from os import path



MAX_SECS = 10

def convertToTSV(jsonFile):
    with open(jsonFile) as f:
        a = json.load(f)
        return a


def shouldAdd(file_size, label, time_ms):
    if file_size == -1:
        # Excluding samples that failed upon conversion
        return False
    elif label is None:
        # Excluding samples that failed on label validation
        return False
    elif int(time_ms *1000/10/2) < len(str(label)):
        # Excluding samples that are too short to fit the transcript
        # print(f'too short {time_ms /1000.0}')
        return False
    elif time_ms / 1000 > MAX_SECS:
        # Excluding very long samples to keep a reasonable batch-size
        # print(f'too long {time_ms /1000}')
        return False
    else:
        # This one is good - keep it for the target CSV
        return True

def main(args):

    a = convertToTSV(args.jsonIn)
    audio = AudioSegment.from_mp3(args.audioIn)
    # create the same structure as the example tsv except client id
    tsvOut = {'wav_filename':[], 'wav_filesize':[], 'transcript':[]}

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

            if 'end_time' not in items[endIndex] and endTimeMS != -1 and startTimeMS != -1:
                # then we reached end of a sentence
                # now split the audio and save it out in format for deepspeech
                audioSeg = audio[startTimeMS:endTimeMS]
                # write out audio 16kHz wav 
                audioSeg.export(f'{args.audio_dir}{os.sep}segment{i}_{j}.wav', format='wav', parameters=['-ar', '16000'])

                file_size = path.getsize(f'{args.audio_dir}{os.sep}segment{i}_{j}.wav')


                startTimeMS = -1 # need to find the next start time
                endTimeMS = -1 # need to find the next end time
                if shouldAdd(file_size, transcript, len(audioSeg)):
                    # and now add a line to the tsv
                    tsvOut['wav_filename'].append(f'{args.audio_dir}{os.sep}segment{i}_{j}.wav')
                    tsvOut['transcript'].append(transcript)
                    tsvOut['wav_filesize'].append(file_size)

                j = j + 1
                transcript = ''


    pd.DataFrame(tsvOut).to_csv(args.tsvOut,index=False)

if __name__ == '__main__':
    # for example
    # create a folder called segments inside the directory with 
    # python tsvcreator.py -i ../data/452020.mp3 -j ../data/asrOutput.json -o ./segments -t ./segments/deepspeech.csv
    # should place the created csv in the same directory as the segments
    parser = argparse.ArgumentParser(description='convert audio to csv and split into segments for DeepSpeech.')
    parser.add_argument('-i', action='store', help='Audio input mp3 file', dest='audioIn')
    parser.add_argument('-j', action='store', help='json trascription file input from aws', dest='jsonIn')
    parser.add_argument('-o', action='store', help='The folder to store the audio segments', dest='audio_dir', default='')
    parser.add_argument('-t', action='store', help='The file to store the deepSpeech tsv file', dest='tsvOut')
    # I don't think we need to do this
    # parser.add_argument('--normalize', action='store_true', help='Converts diacritic characters to their base ones')
    # parser.add_argument('--filter_alphabet', help='Exclude samples with characters not in provided alphabet')
    # parser.add_argument('--space_after_every_character', action='store_true', help='To help transcript join by white space')

    args = parser.parse_args()
    main(args)
