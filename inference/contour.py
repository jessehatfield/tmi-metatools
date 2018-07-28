#!/usr/bin/env python

import matplotlib.pyplot as plt
import pandas
import seaborn as sns
import sys

def read_sample_file(filename):
    i = 0
    lastcomment = 0
    beforedata = 0
    ncomments = 0
    commentblocksize = 0
    with open(filename) as text:
        for line in text:
            i += 1
            if line.startswith('#'):
                commentblocksize += 1
                lastcomment = i
            elif commentblocksize > 0:
                ncomments += commentblocksize
                beforedata = lastcomment
                commentblocksize = 0
    df = pandas.read_csv(filename, comment='#', header=0)
    skiplines = beforedata - ncomments - 1
    return df[skiplines:]

def read_sample_files(filenames):
    frames = [read_sample_file(f) for f in filenames]
    return pandas.concat(frames)

def plot_bivariate(df, xvars, yvars):
    g = None
    k = min(len(xvars), len(yvars))
    pal = sns.color_palette()
    for i in range(k):
        var1 = xvars[i]
        var2 = yvars[i]
        print("Plotting {} x {}...".format(var1, var2))
        if g is None:
            g = sns.JointGrid(var1, var2, df, xlim=(0,1), ylim=(0,1))
        plot = sns.kdeplot(df[var1], df[var2], ax=g.ax_joint, shade=True,
                shade_lowest=False)
        xax = sns.kdeplot(df[var1], ax=g.ax_marg_x, legend=False)
        sns.rugplot(df[var1], ax=xax, color=pal[i])
        yax = sns.kdeplot(df[var2], ax=g.ax_marg_y, vertical=True, legend=False)
        sns.rugplot(df[var2], ax=yax, vertical=True, color=pal[i])
    return g

filenames = sys.argv[1:]

df = read_sample_files(filenames).sample(1000)
pdeck = [col for col in df.columns if col.startswith('pdeck')]
pwin = [col for col in df.columns if col.startswith('pwin_deck')]

g = plot_bivariate(df, pdeck, pwin)
g.set_axis_labels("Proportion of Field", "Match Win Probability")

plt.show()
