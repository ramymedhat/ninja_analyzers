import os
import sys
import argparse
import bashlex

parser = argparse.ArgumentParser(description='Tool to categorize commands run within the android'
         ' build. Use with a version of ninja log that is formatted as follows: \n'
         'start\\tend\\ttimestamp\\toutput\\tcommand')

parser.add_argument('log_file', help='ninja log file to categorize.')
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
    for p in node.parts:
        if p.kind == 'word':
            if p.word == '[':
                word = p.word
                continue
            if p.word == '/bin/bash':
                continue
            if len(p.word) > 0 and p.word[0] == '-':
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
    #print cmd
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
                cmd_map[word][cmd_tuple[0]] = cmd_tuple[1:]
                done_cmds.add(cmd_tuple)

done_cmds = set()
cmds = load_commands(args.log_file)
cmds = sanitize_commands(cmds)
cmd_map = {}
for idx, c in enumerate(cmds[94555:110000]):
    print (idx, len(cmd_map), [k for k in cmd_map][:5])
    try:
        parse_cmd(cmd_map, c, c[0])
        if c not in done_cmds:
            print 'Missing'
            exit()
    except Exception as e:
        print e

print len(cmd_map)
