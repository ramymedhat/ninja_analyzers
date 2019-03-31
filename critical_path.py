import os
import sys
import argparse
import bashlex
import math
from multiprocessing import Process, Manager
import pickle
import re

parser = argparse.ArgumentParser(description='Tool to compute the critical path in a ninja'
         ' build using the ninja graph tool. Use with a version of ninja that dumps nodes '
         ' for multi output edges. Modification should be in graphviz.cc')

parser.add_argument('graph_file', help='Graph file.')
parser.add_argument('log_file', help='ninja log file to categorize.')
args = parser.parse_args()

re_node = r'^\"(0x[a-f0-9]+)\" \[label=\"(.*?)\".*\]$'
re_edge = r'^\"(0x[a-f0-9]+)\" -> \"(0x[a-f0-9]+)\"'

def load_commands(path):
    f = open(path, 'r')
    lines = f.readlines()
    lines = [l for l in lines if len(l) > 0 and l[0] != '#']
    cmds = [l.split('\t') for l in lines]
    cmds = [(" ".join(c[5:]), int(c[1]) - int(c[0]), c[3]) for c in cmds]
    return cmds

def load_graph(path):
    lines = open(path, 'r').readlines()
    nodes = {}
    roots = {}
    leaves = {}
    edges = {}
    cnt_edges = 0
    for line in lines:
        res = re.search(re_node, line)
        if res != None:
            nodes[res.group(1)] = res.group(2)
            roots[res.group(1)] = res.group(2)
            leaves[res.group(1)] = res.group(2)
            #print 'node %s[%s] (%d)' % (res.group(1), res.group(2), len(nodes))
    for line in lines:
        res = re.search(re_edge, line)
        if res != None:
            cnt_edges += 1
            src,dest = res.group(1), res.group(2)
            #print 'edge %s[%s]' % (src,dest)
            if src not in edges:
                edges[src] = set()
            edges[src].add(dest)
            roots.pop(dest, None)
            leaves.pop(src, None)
            continue
    return nodes, roots, leaves, edges

def map_cmds_to_graph(nodes, cmds):
    out_cmds = {}
    cmd_outs = {}
    cmd_nodes = {}
    for c in cmds:
        out_cmds[c[2]] = (c[0], c[1])
        if c[0] not in cmd_outs:
            cmd_outs[c[0]] = set()
        cmd_outs[c[0]].add(c[2])
        cmd_nodes[c[0]] = set()
    node_cmds = {}
    for n in nodes:
        if nodes[n] in out_cmds:
            cmd,dur = out_cmds[nodes[n]]
            node_cmds[n] = (cmd,dur)
            cmd_nodes[cmd].add(n)
    return node_cmds

nodes, roots, leaves, edges = load_graph(args.graph_file)
print len(nodes), len(roots), len(leaves), sum([len(edges[k]) for k in edges])
cmds = load_commands(args.log_file)
node_cmds = map_cmds_to_graph(nodes, cmds)

sol_cache = {}
def cpath(edges, node_cmds, node):
    if node in sol_cache:
        return sol_cache[node]
    time = node_cmds[node][1] if node in node_cmds else 0
    max_dur = 0
    max_path = []
    if node not in edges:
        return time, [node]
    for child in edges[node]:
        dur,path = cpath(edges, node_cmds, child)
        if dur > max_dur:
            max_dur, max_path = dur, path

    # Make sure no command is counted twice
    child_cmds = [node_cmds[c][0] for c in max_path if c in node_cmds]
    if node in node_cmds and node_cmds[node][0] in child_cmds:
        time = 0

    sol_cache[node] = (max_dur+time, [node] + max_path)
    return sol_cache[node]

max_dur = 0
max_path = []
idx = 0
for node in roots:
    if idx % 5000 == 0:
        print (idx, len(roots))
    idx += 1
    dur,path = cpath(edges, node_cmds, node)
    if dur > max_dur:
        max_dur, max_path = dur, path
print max_dur
for node in max_path:
    print 'Dur: %d' % (node_cmds[node][1] if node in node_cmds else 0)
    print 'Cmd(target): %s' % (node_cmds[node][0].strip() if node in node_cmds else nodes[node])
