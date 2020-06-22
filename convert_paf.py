#!/usr/bin/env python
import argparse
import os 
import sys
import pandas as pd
import re
header = ["q_name", "q_len", "q_st", "q_en", "strand",
               "t_name", "t_len", "t_st", "t_en", "matches", "aln_len", "mapq"]
ctype = [str, int, int, int, str, str, int, int, int, int, int, int]
ncol = len(header)


def read_paf(f):
    rtn = {}
    for name in header: rtn[name] = []
        
    for idx, line in enumerate(open(f)):
        t = line.strip().split()
        if(t[5] == "*"): continue # skip paf no hit lines 
        
        for name, typ, val in zip(header, ctype, t[:ncol]):
            rtn[name].append(typ(val))
        
        # add the tags 
        for val in t[ncol:]:
            match = re.match("(..):(.):(.*)", val)
            tag, typ, val = match.groups()
            if(tag == "cg"): continue # skip the cg tag to keep the tabl size not huge 

            if(tag not in rtn): rtn[tag] = []
            
            if(typ == "i"):
                rtn[tag].append(int(val))
            elif(typ == "f"):
                rtn[tag].append(float(val))
            else:
                rtn[tag].append(val)
        sys.stderr.write(f"\r{idx}") 
    # drop tags not in all pafs 
    nrows = len(rtn["q_name"])
    remove = []
    for name in rtn:
        if(len(rtn[name]) != nrows): remove.append(name)
    for name in remove: del rtn[name] 
    return(rtn)

def read_dict(paf_d, NCOLORS, minq):
    df = pd.DataFrame(paf_d)
    assert "de" == "de"
    df["identity"] = 100 - 100*df["de"]
    MINID = int(df.identity.quantile(minq))
    df = df.loc[df.identity >= MINID]
	
    
    df["cut"] = pd.qcut( df["identity"], NCOLORS, duplicates="drop")
    df["cutid"] = pd.qcut( df["identity"], NCOLORS, duplicates="drop", labels=False)
    NCOLORS = len(df.cutid.unique())
    
    # if the contig name is not unqiue, check for a split fasta, and then if exit if multiple queries 
    if(len(df.q_name.unique())!=1):
        split = df.q_name.str.extract('(.+):(\d+)-(\d+)', expand=True)
        assert len(split[0].unique()) == 1, "There can be only one query contig"
        offset = split[1].astype(int)
        df.q_st = df.q_st + offset
        df.q_en = df.q_en + offset
        df.q_name = split[0]
        df.q_len = df.q_len.sum()		
	
	
	# set up the x and y names
    rc = ( df.strand == "-")
    df["x1"] = df["t_st"]
    df["x2"] = df["t_en"]
    df["y1"] = df["q_st"]
    df["y2"] = df["q_en"]
    df.loc[rc, "y1"] = df["q_en"][rc]
    df.loc[rc, "y2"] = df["q_st"][rc]
    
    df = df[header + ["x1","x2","y1", "y2", "identity", "cutid"]]
    return(df)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument("infile", help="input paf with cigar string!")
	parser.add_argument("outfile", help="output table with segments to draw in r")
	parser.add_argument("-n", help="number of colors ", type=int, default=10)
	parser.add_argument("-l", help="Remove the lowest quntile of alignemtns (default 0.5%)", type=float, default=0.005)
	parser.add_argument('-d', help="store args.d as true if -d",  action="store_true", default=False)
	args = parser.parse_args()
	
	paf_d = read_paf(args.infile)
	df = read_dict(paf_d, NCOLORS=10, minq=args.l)
	df.to_csv(args.outfile, index=False, sep="\t")


