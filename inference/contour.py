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
    nblocks = 0
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
                nblocks += 1
    df = pandas.read_csv(filename, comment='#', header=0)
    if nblocks > 1:
        skiplines = beforedata - ncomments - 1
    else:
        skiplines = beforedata
    return df[skiplines:]

def read_sample_files(filenames):
    frames = [read_sample_file(f) for f in filenames]
    return pandas.concat(frames)

def read_archetypes(filename):
    archetypes = []
    with open(filename) as text:
        for line in text:
            archetypes.append(line.strip())
    return archetypes

def plot_bivariate(df, xvars, yvars, xlim=(0,.2), ylim=(0.4,0.6)):
    g = None
    k = min(len(xvars), len(yvars))
    pal = sns.color_palette()
    for i in range(k):
        var1 = xvars[i]
        var2 = yvars[i]
        print("Plotting {} x {}...".format(var1, var2))
        if g is None:
            g = sns.JointGrid(var1, var2, df, xlim=xlim, ylim=ylim)
        plot = sns.kdeplot(df[var1], df[var2], ax=g.ax_joint, shade=False,
                shade_lowest=False)
        xax = sns.kdeplot(df[var1], ax=g.ax_marg_x, legend=False)
        rpx = sns.rugplot(df[var1], ax=xax, color=pal[i % len(pal)])
        yax = sns.kdeplot(df[var2], ax=g.ax_marg_y, vertical=True, legend=False)
        rpy = sns.rugplot(df[var2], ax=yax, vertical=True, color=pal[i % len(pal)])
    handles, labels = g.ax_marg_x.get_legend_handles_labels()
    g.ax_joint.legend(handles, labels, loc='lower left')
    g.ax_joint.grid(linestyle='--', color='gray')
    g.ax_joint.axhline(0.5, linestyle='-', color='black', linewidth=0.5)
    return g

title = sys.argv[1]
archetype_file = sys.argv[2]
sample_files = sys.argv[3:]
reverse=False

df = read_sample_files(sample_files)
archetypes = read_archetypes(archetype_file)
print(archetypes)

pwin = [col for col in df.columns if col.startswith('pwin_deck')]
df.rename({"pdeck.{}".format(i+1): archetypes[i] for i in
    range(len(archetypes))}, inplace=True, axis="columns")

if reverse:
    g = plot_bivariate(df, pwin, archetypes)
    g.set_axis_labels("Match Win Probability", "Proportion of Field")
else:
    g = plot_bivariate(df, archetypes, pwin)
    g.set_axis_labels("Proportion of Field", "Match Win Probability")
g.fig.suptitle(title)

plt.show()
