#!/usr/bin/env python3

import sys
import csv
import argparse
import math
import random
import grpc
import numpy as np
import librosa

from detector_pb2 import DetectorRequest
from detector_pb2_grpc import DeepfakeDetectorStub


def to_mono(samples: np.ndarray) -> np.ndarray:
    if samples.ndim == 1:
        return samples
    else:
        print('Converting to mono', file=sys.stderr)
        return np.mean(samples, axis=tuple(range(samples.ndim - 1)))


def normalize(samples: np.ndarray) -> np.ndarray:
    x_max = np.max(samples)
    x_min = np.min(samples)
    x = samples / max(abs(x_max), abs(x_min))
    return x


def main():
    argparser = argparse.ArgumentParser(
        description='Submits audio samples to the deepfake detector for classification.',
        epilog='Upon successful execution the exit code will be a number in the 0 - 100 ' +
        'range, representing the degree of certainty that the audio is authentic.')
    argparser.add_argument('-f', '--file',
                           action='store',
                           required=True,
                           help='File from which to extract audio samples.')
    argparser.add_argument('-n', '--num-slices',
                           action='store',
                           default=3,
                           type=int,
                           help='Number of audio slices to extract. Each slice contains 1 second ' +
                           'worth of audio.')
    argparser.add_argument('-u', '--uri',
                           action='store',
                           required=True,
                           help='Detector service uri (format <host>:<port>).')
    argparser.add_argument('-o', '--offset',
                           action='store',
                           type=int,
                           default=-1,
                           help='Index of the slice from which to start extracting data. If ' +
                           'unspecified the slices will be selected from random locations.')
    argparser.add_argument('-T', '--target-sample-rate',
                           action='store',
                           default=16000,
                           type=int,
                           help='The extracted audio slices will be resampled to match this ' +
                           'sample rate, if necessary. Expressed in Hz.')
    argparser.add_argument('-s', '--single-slice',
                           action='store_true',
                           default=True,
                           help='Submit slices one at a time. Do not batch them.')
    argparser.add_argument('-c', '--csv',
                           action='store_true',
                           default=True,
                           help='Format output as CSV.')

    args = argparser.parse_args()

    try:
        data, sr = librosa.load(args.file, sr=args.target_sample_rate)
    except Exception as e:
        print(f'{args.file}: {e}')
        return -1

    data = to_mono(data)

    slices_available = math.floor(len(data) / sr)
    slice_count = min(slices_available, args.num_slices)

    print(f'{args.file}: sampling rate = {sr} Hz', file=sys.stderr)
    print(f'{args.file}: slice count = {slice_count}', file=sys.stderr)
    print(f'{args.file}: slices available = {slices_available}', file=sys.stderr)

    offset = args.offset
    if offset != -1:
        last = min(offset + slice_count, slices_available)
        indices = list(range(offset, last))
    else:
        indices = random.sample(range(slices_available), slice_count)

    results: list[float] = []

    if args.single_slice:
        # Single slice -- extracts 1 second slices from the audio file and
        # submits them for processing immediately. We will get a separate
        # certainty value for each slice.
        with grpc.insecure_channel(args.uri) as channel:
            stub = DeepfakeDetectorStub(channel)
            for index in indices:
                request = DetectorRequest()
                off = sr * index
                samples = normalize(data[off:off+sr])
                slice = request.slices.add()
                slice.samples = samples.tobytes()
                response = stub.Analyze(request)
                results.append(response.certainty)
    else:
        # Slice batching -- extracts 1 second slices from the audio file,
        # adds them to the request and then submits them as a batch.
        # The service will respond with a mean certainty value.
        request = DetectorRequest()
        for index in indices:
            off = sr * index
            samples = normalize(data[off:off+sr])
            slice = request.slices.add()
            slice.samples = samples.tobytes()
        with grpc.insecure_channel(args.uri) as channel:
            stub = DeepfakeDetectorStub(channel)
            response = stub.Analyze(request)
            results.append(response.certainty)

    if args.csv:
        csv_writer = csv.writer(sys.stdout)
        for i, r in zip(indices, results):
            csv_writer.writerow([i, r])
    else:
        print(results)

    if args.single_slice:
        exit(0)
    else:
        exit(round(response.certainty * 100))


if __name__ == '__main__':
    main()
