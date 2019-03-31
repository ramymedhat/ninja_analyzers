import os
import sys
import argparse
import bashlex
import math
from multiprocessing import Process, Manager
import pickle

parser = argparse.ArgumentParser(description='Tool to categorize commands run within the android'
         ' build. Use with a version of ninja log that is formatted as follows: \n'
         'start\\tend\\ttimestamp\\toutput\\tcommand')

parser.add_argument('log_file', help='ninja log file to categorize.')
parser.add_argument('--skip_processing', help='set to load preprocessed pkl files.', action="store_true")
args = parser.parse_args()

def load_commands(path):
    f = open(path, 'r')
    lines = f.readlines()
    lines = [l for l in lines if len(l) > 0 and l[0] != '#']
    cmds = [l.split('\t') for l in lines]
    cmds = [(" ".join(c[5:]), int(c[1]) - int(c[0]), c[3]) for c in cmds]
    return cmds

def sanitize_commands(cmds):
    cmds = [(c[0].split('rspfile')[0], c[1], c[2]) for c in cmds]
    return cmds

def command_word(node):
    if node.kind != 'command':
        return ''
    word = ''
    is_bash = False
    for p in node.parts:
        if p.kind == 'word':
            if p.word == '[':
                word = p.word
                continue
            if p.word == '/bin/bash':
                is_bash = True
                continue
            if is_bash and len(p.word) > 0 and p.word[0] == '-':
                continue
            word += p.word
            break
    #print 'Found word %s' % word
    return word

def find_words_in_tree(node):
    words = []
    #print node.dump()
    if node.kind == 'command':
        return [command_word(node)]
    parts = None
    if hasattr(node, 'parts'):
        parts = node.parts
    if hasattr(node, 'list'):
        parts = node.list
    if parts == None:
        return []
    for p in parts:
        if p.kind == 'command':
            #print 'Found command in part'
            words.append(command_word(p))
        else:
            words.extend(find_words_in_tree(p))
    return words

def parse_cmd(cmd_map, cmd_tuple, cmd):
    parts = bashlex.parse(cmd)
    for part in parts:
        words = find_words_in_tree(part)
        if len(words) == 0:
            continue
        for word in words:
            if ' ' in word:
                parse_cmd(cmd_map, cmd_tuple, word)
            else:
                if word not in cmd_map:
                    cmd_map[word] = {}
                key = (cmd_tuple[0],cmd_tuple[1])
                if key not in cmd_map[word]:
                    cmd_map[word][key] = []
                cmd_map[word][key].append(cmd_tuple[2])
                done_cmds.add(cmd_tuple)

def process(start, end):
    cmds = load_commands(args.log_file)
    cmds = sanitize_commands(cmds)
    cmds = cmds[start:end]
    cmd_map = {}
    for idx, c in enumerate(cmds):
        try:
            parse_cmd(cmd_map, c, c[0])
            if c not in done_cmds:
                print 'Missing'
                exit()
        except Exception as e:
            print 'Failed to parse command due to %s, adding as is' % e
            key = (c[0],c[1])
            cmd_map[c[0]] = {key: [c[2]]}
    pickle.dump(cmd_map, open( 'categories_%i_%i.pkl' % (start, end), 'wb'))

def fork(parts):
    manager = Manager()
    processes = []
    for start,end in parts:
        print start, end
        p = Process(target=process, args=(start, end))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

def split_work(cmds):
    cpu_count = 64.0
    share = int(math.ceil(len(cmds)/cpu_count/100)*100)
    parts = []
    for i in range(int(cpu_count)):
        start,end = i*share,(i+1)*share
        parts.append((start,end))
    return parts

done_cmds = set()
cmds = load_commands(args.log_file)
cmds = sanitize_commands(cmds)
cmd_map = {}
threads = []
parts = split_work(cmds)
if not args.skip_processing:
    fork(parts)

for start,end in parts:
    sub_cmd_map = pickle.load( open( 'categories_%i_%i.pkl' % (start,end), 'rb' ) )
    for k in sub_cmd_map:
        if k in cmd_map:
            cmd_map[k].update(sub_cmd_map[k])
        else:
            cmd_map[k] = sub_cmd_map[k]

cmd_combos = {}
for c in cmds:
    key = (c[0],c[1])
    bins = set()
    for k in cmd_map:
        if key in cmd_map[k]:
            bins.add(k)
    bins = ";".join(sorted(list(bins)))
    if bins not in cmd_combos:
        cmd_combos[bins] = {}
    if key not in cmd_combos[bins]:
        cmd_combos[bins][key] = []
    cmd_combos[bins][key].append(c[2])

for bins in cmd_combos:
    keys = cmd_combos[bins].keys()
    durs = [k[1] for k in keys]
    print (bins,len(durs),max(durs),sum(durs)/float(len(durs)))
