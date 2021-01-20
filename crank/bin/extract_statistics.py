#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (c) 2020 Kazuhiro KOBAYASHI <root.4mac@gmail.com>
#
# Distributed under terms of the MIT license.

"""
Extract speaker-independent statistics

"""

import argparse
import h5py
import joblib
import logging
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler

from crank.utils import load_yaml, open_scpdir, open_featsscp

logging.basicConfig(level=logging.INFO)


class Scaler(object):
    def __init__(self):
        self.ss = StandardScaler()

    def partial_fit(self, data):
        self.ss.partial_fit(data)

    def fit(self, file_lists, ext="mcep"):
        for h5f in file_lists:
            with h5py.File(h5f, "r") as fp:
                data = fp[ext][:]
                if len(data.shape) == 1:
                    data = data[:, np.newaxis]
                self.partial_fit(data)


def main():
    dcp = "Extract feature statistics"
    parser = argparse.ArgumentParser(description=dcp)
    parser.add_argument("--n_jobs", type=int, default=-1, help="# of CPUs")
    parser.add_argument("--phase", type=str, default=None, help="phase")
    parser.add_argument("--conf", type=str, help="ymal file for network parameters")
    parser.add_argument("--scpdir", type=str, help="scp directory")
    parser.add_argument("--featdir", type=str, help="output feature directory")
    args = parser.parse_args()

    conf = load_yaml(args.conf)
    scp = open_scpdir(Path(args.scpdir) / args.phase)
    featdir = Path(args.featdir) / conf["feature"]["label"]
    featsscp = featdir / args.phase / "feats.scp"
    scp["feats"] = open_featsscp(featsscp)
    scaler = {}

    # speaker independent scaler extraction
    feats = ["mlfb", "mcep", "lcf0", "cenergy"]
    for win_type in conf["feature"]["window_types"]:
        if win_type != "hann":
            feats += [f"mlfb_{win_type}"]
            feats += [f"lsp_{win_type}"]

    for ext in feats:
        s = Scaler()
        s.fit(list(scp["feats"].values()), ext=ext)
        logging.info("# of samples for {}: {}".format(ext, s.ss.n_samples_seen_))
        scaler[ext] = s.ss

    # speaker dependent statistics extraction
    sd_feats = ["lcf0", "cenergy"]
    for ext in sd_feats:
        for spkr in scp["spkrs"]:
            file_lists_sd = [scp["feats"][uid] for uid in scp["spk2utt"][spkr]]
            s = Scaler()
            s.fit(file_lists_sd, ext=ext)
            logging.info(
                "# of samples {} of {}: {} samples".format(
                    ext, spkr, s.ss.n_samples_seen_
                )
            )
            if spkr not in scaler.keys():
                scaler[spkr] = {}
            scaler[spkr][ext] = s.ss

    pklf = featdir / "scaler.pkl"
    joblib.dump(scaler, str(pklf))
    logging.info("Save scaler to {}".format(pklf))


if __name__ == "__main__":
    main()
