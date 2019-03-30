import os
import sys
import argparse
import bashlex

parser = argparse.ArgumentParser(description='Tool to categorize commands run within the android'
         ' build. Use with a version of ninja log that is formatted as follows: \n'
         'start\\tend\\ttimestamp\\toutput\\tcommand')

parser.add_argument('log_file', help='ninja log file to categorize.')

def load_commands(path):
    f = open(path, 'r')
    lines = f.readlines()
    lines = [l for l in lines if len(l) > 0 and l[0] != '#']
    cmds = [l.split('\t') for l in lines]
    cmds = [(" ".join(c[5:]), int(c[1]) - int(c[0]), c[3]) for c in cmds]
    return cmds

def sanitize_commands(cmds):
    return cmds

def command_word(node):
    
